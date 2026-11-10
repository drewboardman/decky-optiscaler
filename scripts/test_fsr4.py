#!/usr/bin/env python3
"""Offline integration tests for the Deck preset's DLL/settings lifecycle."""
import ast
import asyncio
import hashlib
import io
import logging
from contextlib import redirect_stdout
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'py_modules'))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import pin_fsr4_build
from optiscaler import installer, fsr4build
from optiscaler.constants import FFX_UPSCALER_DLL, INI_NAME, MANIFEST_NAME
from optiscaler.inifile import IniFile
from optiscaler.service import OptiScalerService

ROOT = Path(__file__).resolve().parents[1]

#: These tests are about the fetch/install machinery, not about which build is
#: pinned, so they carry a synthetic build rather than borrowing an entry from
#: the table — otherwise the constants moving to a new build renames every
#: assertion in this file out from under it.
TEST_BUILD_ID = 'test-build'


class BuildFetchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        fsr4build._digests.clear()
        self.dll_bytes = b'verified upscaler DLL'
        sources = [
            {'repo': 'example/primary', 'tag': 'v1', 'asset': 'build.7z'},
            {'repo': 'example/mirror', 'tag': 'v1', 'asset': 'build-mirror.7z'},
        ]
        self.build = {
            'id': TEST_BUILD_ID,
            'label': 'Test build',
            'note': '',
            'file': FFX_UPSCALER_DLL,
            'file_bytes': len(self.dll_bytes),
            'file_sha256': hashlib.sha256(self.dll_bytes).hexdigest(),
            'reaches_fsr4_by': 'int8',
            'sources': [dict(source, archive_sha256=hashlib.sha256(
                source['repo'].encode()).hexdigest()) for source in sources],
        }

    def download(self, url, archive, **kwargs):
        source = next(s for s in self.build['sources'] if fsr4build.url_for(s) == url)
        archive.parent.mkdir(parents=True, exist_ok=True)
        archive.write_bytes(source['repo'].encode())

    def extract(self, archive, target, logger=None):
        target.mkdir(parents=True, exist_ok=True)
        (target / self.build['file']).write_bytes(self.dll_bytes)

    def test_two_files_remain_cached_and_changes_are_rehashed(self):
        paths = [self.root / name for name in ('game.dll', 'cached.dll')]
        for path in paths:
            path.write_bytes(self.dll_bytes)
        with patch.object(fsr4build.payload, 'sha256', wraps=fsr4build.payload.sha256) as sha:
            for _ in range(3):
                for path in paths:
                    fsr4build.digest(path)
            self.assertEqual(sha.call_count, 2)
            paths[0].write_bytes(b'changed DLL')
            self.assertNotEqual(fsr4build.digest(paths[0]), self.build['file_sha256'])
            self.assertEqual(sha.call_count, 3)
            for i in range(10):
                path = self.root / str(i)
                path.write_bytes(b'other DLL')
                fsr4build.digest(path)
            self.assertLessEqual(len(fsr4build._digests), 8)

    def test_identification_skips_unknown_sizes_but_checks_known_sizes(self):
        path = self.root / 'game.dll'
        path.write_bytes(b'unknown size')
        with patch.object(fsr4build, 'FSR4_BUILDS', [self.build]), \
                patch.object(fsr4build.payload, 'sha256', wraps=fsr4build.payload.sha256) as sha:
            self.assertFalse(fsr4build.identify(path)['known'])
            sha.assert_not_called()
            path.write_bytes(self.dll_bytes)
            self.assertEqual(fsr4build.identify(path)['id'], self.build['id'])
            path.write_bytes(b'x' * len(self.dll_bytes))
            self.assertFalse(fsr4build.identify(path)['known'])

    def test_primary_failure_uses_mirror_and_reuses_verified_cache(self):
        def download(url, archive, **kwargs):
            if url == fsr4build.url_for(self.build['sources'][0]):
                raise OSError('release deleted')
            self.download(url, archive, **kwargs)
        with patch.object(fsr4build.wiki, 'download', side_effect=download) as get, \
                patch.object(fsr4build.payload, 'extract_archive', side_effect=self.extract):
            path = fsr4build.fetch(self.build, self.root)
            self.assertEqual(path.read_bytes(), self.dll_bytes)
            self.assertEqual(get.call_count, 2)
            self.assertEqual(fsr4build.fetch(self.build, self.root), path)
            self.assertEqual(get.call_count, 2)

    def test_corrupt_primary_archive_falls_back(self):
        def download(url, archive, **kwargs):
            self.download(url, archive, **kwargs)
            if url == fsr4build.url_for(self.build['sources'][0]):
                archive.write_bytes(b'corrupt archive')
        with patch.object(fsr4build.wiki, 'download', side_effect=download), \
                patch.object(fsr4build.payload, 'extract_archive', side_effect=self.extract) as extract:
            self.assertEqual(fsr4build.fetch(self.build, self.root).read_bytes(), self.dll_bytes)
            self.assertEqual(extract.call_count, 1)

    def test_wrong_dll_from_either_source_is_rejected(self):
        def extract(archive, target, logger=None):
            self.extract(archive, target, logger)
            (target / self.build['file']).write_bytes(b'x' * len(self.dll_bytes))
        with patch.object(fsr4build.wiki, 'download', side_effect=self.download) as get, \
                patch.object(fsr4build.payload, 'extract_archive', side_effect=extract):
            with self.assertRaisesRegex(RuntimeError, 'DLL checksum mismatch'):
                fsr4build.fetch(self.build, self.root)
            self.assertEqual(get.call_count, 2)
            self.assertFalse(fsr4build.cached_path(self.root, self.build).exists())

    def test_failed_extraction_cannot_leave_a_dll_for_the_mirror(self):
        attempts = 0
        def extract(archive, target, logger=None):
            nonlocal attempts
            attempts += 1
            if attempts == 1:
                self.extract(archive, target, logger)
                raise RuntimeError('incomplete extraction')
            target.mkdir(parents=True, exist_ok=True)
        with patch.object(fsr4build.wiki, 'download', side_effect=self.download), \
                patch.object(fsr4build.payload, 'extract_archive', side_effect=extract):
            with self.assertRaisesRegex(RuntimeError, 'did not contain'):
                fsr4build.fetch(self.build, self.root)

    def local_source(self, name, archive_bytes):
        """A source that is the plugin's own copy rather than a release."""
        return {'local': True, 'asset': name,
                'archive_sha256': hashlib.sha256(archive_bytes).hexdigest()}

    def test_a_shipped_build_is_read_where_it_is_shipped(self):
        shipped = self.root / 'bin'
        shipped.mkdir()
        carried = b'the archive that was carried here'
        archive = shipped / 'FSR_4.1.1d_INT8.7z'
        archive.write_bytes(carried)
        build = dict(self.build, id='4.1.1d',
                     sources=[self.local_source(archive.name, carried)])
        with patch.object(fsr4build, 'url_for',
                          side_effect=AssertionError('a shipped archive has no URL')), \
                patch.object(fsr4build.wiki, 'download') as get, \
                patch.object(fsr4build.payload, 'extract_archive', side_effect=self.extract):
            path = fsr4build.fetch(build, self.root / 'cache', local_dir=shipped)
            self.assertEqual(path.read_bytes(), self.dll_bytes)
            get.assert_not_called()
        # The shipped archive is part of the install: read, never moved or removed.
        self.assertEqual(archive.read_bytes(), carried)

    def test_a_shipped_build_that_is_not_there_says_which_file(self):
        build = dict(self.build, id='4.1.1d',
                     sources=[self.local_source('FSR_4.1.1d_INT8.7z', b'missing')])
        for kwargs in ({'local_dir': self.root / 'bin'}, {}):
            with self.assertRaisesRegex(
                    RuntimeError, 'FSR_4.1.1d_INT8\\.7z is not shipped with this plugin'):
                fsr4build.fetch(build, self.root / 'cache', **kwargs)

    def test_a_shipped_archive_that_is_not_the_pinned_one_is_left_alone(self):
        shipped = self.root / 'bin'
        shipped.mkdir()
        archive = shipped / 'FSR_4.1.1d_INT8.7z'
        archive.write_bytes(b'edited after it was pinned')
        build = dict(self.build, id='4.1.1d',
                     sources=[{'local': True, 'asset': archive.name,
                               'archive_sha256': 'b' * 64}])
        with self.assertRaisesRegex(RuntimeError, 'archive checksum mismatch'):
            fsr4build.fetch(build, self.root / 'cache', local_dir=shipped)
        # Deleting a file the plugin shipped would be worse than the mismatch.
        self.assertTrue(archive.is_file())

    def test_a_build_can_carry_one_copy_and_download_another(self):
        shipped = self.root / 'bin'
        shipped.mkdir()
        build = dict(self.build, id='4.1.1d',
                     sources=[{'local': True, 'asset': 'FSR_4.1.1d_INT8.7z',
                               'archive_sha256': 'c' * 64},
                              *[dict(source) for source in self.build['sources']]])
        with patch.object(fsr4build.wiki, 'download', side_effect=self.download) as get, \
                patch.object(fsr4build.payload, 'extract_archive', side_effect=self.extract):
            path = fsr4build.fetch(build, self.root / 'cache', local_dir=shipped)
            self.assertEqual(path.read_bytes(), self.dll_bytes)
            self.assertEqual(get.call_count, 1)
            self.assertEqual(fsr4build.fetch(build, self.root / 'cache', local_dir=shipped), path)
            self.assertEqual(get.call_count, 1)

    def test_a_build_with_no_source_says_so(self):
        with self.assertRaisesRegex(ValueError, 'no source is pinned'):
            fsr4build.fetch(dict(self.build, sources=[]), self.root / 'cache')


class DeckFsr4Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.service = OptiScalerService(ROOT, self.root/'settings', self.root/'runtime',
                                        self.root/'home', logging.getLogger('test'))
        self.payload = asyncio.run(self.service.ensure_payload())
        self.target = self.root/'game'
        self.target.mkdir()
        (self.target/FFX_UPSCALER_DLL).write_bytes(b'original game DLL')
        installer.install(self.target, self.payload)
        ini = IniFile(self.target/INI_NAME)
        ini.set('FrameGen', 'FGOutput', 'fsr3')
        ini.save()
        self.dll = self.root/'pinned.dll'
        self.dll.write_bytes(b'test upscaler DLL')
        self.build = {
            'id': TEST_BUILD_ID,
            'label': 'Test build',
            'note': '',
            'file': FFX_UPSCALER_DLL,
            'file_sha256': hashlib.sha256(self.dll.read_bytes()).hexdigest(),
            'file_bytes': self.dll.stat().st_size,
            'reaches_fsr4_by': 'int8',
        }
        mock = patch.object(fsr4build, 'FSR4_BUILDS', [self.build])
        mock.start()
        self.addCleanup(mock.stop)

    def enable(self):
        with patch.object(fsr4build, 'fetch', return_value=self.dll):
            return asyncio.run(self.service.set_fsr4_build(str(self.target), TEST_BUILD_ID))

    def snapshot(self):
        return {name: (self.target/name).read_bytes()
                for name in [FFX_UPSCALER_DLL, INI_NAME, MANIFEST_NAME]}

    def test_enable_verify_reinstall_restore_uninstall(self):
        self.assertTrue(self.enable()['ok'])
        config = asyncio.run(self.service.read_config(str(self.target)))
        self.assertEqual(config['fsr4_build'], TEST_BUILD_ID)
        self.assertEqual(config['values']['FSR']['Fsr4ForceEnableInt8'], 'true')
        self.assertEqual(config['values']['FSR']['Fsr4Update'], 'auto')
        self.assertEqual(config['values']['FSR']['UpscalerIndex'], '0')
        self.assertEqual(config['values']['FrameGen']['FGOutput'], 'fsr3')
        self.assertTrue(installer.verify_install(self.target, self.payload)['complete'])
        installer.install(self.target, self.payload)
        self.assertEqual((self.target/FFX_UPSCALER_DLL).read_bytes(), self.dll.read_bytes())
        self.assertEqual(installer.read_manifest(self.target)['fsr4_build']['id'], TEST_BUILD_ID)
        installer.restore_fsr4_build(self.target, self.payload)
        self.assertEqual(fsr4build.identify(self.target/FFX_UPSCALER_DLL)['id'], 'bundled')
        self.assertTrue(installer.verify_install(self.target, self.payload)['complete'])
        self.assertTrue(self.enable()['ok'])
        installer.uninstall(self.target)
        self.assertEqual((self.target/FFX_UPSCALER_DLL).read_bytes(), b'original game DLL')

    def test_other_registered_build_is_accepted_and_unknown_is_rejected(self):
        self.build['id'] = 'future-build'
        with patch.object(fsr4build, 'fetch', return_value=self.dll) as fetch:
            result = asyncio.run(self.service.set_fsr4_build(str(self.target), 'future-build'))
            self.assertTrue(result['ok'])
            fetch.reset_mock()
            result = asyncio.run(self.service.set_fsr4_build(str(self.target), 'unknown'))
            self.assertFalse(result['ok'])
            fetch.assert_not_called()

    def test_invalid_preset_rolls_back_settings_and_dll(self):
        before = self.snapshot()
        with patch.object(installer.schema, 'valid', return_value=False):
            self.assertFalse(self.enable()['ok'])
        self.assertEqual(before, self.snapshot())

    def test_download_failure_preserves_settings_and_dll(self):
        before = self.snapshot()
        with patch.object(fsr4build, 'fetch', side_effect=ValueError('checksum mismatch')):
            result = asyncio.run(self.service.set_fsr4_build(str(self.target), TEST_BUILD_ID))
        self.assertFalse(result['ok'])
        self.assertEqual(before, self.snapshot())

    def test_same_size_corruption_fails_verification_and_reinstall(self):
        self.assertTrue(self.enable()['ok'])
        (self.target/FFX_UPSCALER_DLL).write_bytes(b'x'*self.build['file_bytes'])
        self.assertIn(FFX_UPSCALER_DLL, installer.verify_install(self.target, self.payload)['problems'])
        before = self.snapshot()
        with self.assertRaises(ValueError):
            installer.install(self.target, self.payload)
        self.assertEqual(before, self.snapshot())
        self.assertTrue(self.enable()['ok'])
        self.assertTrue(installer.verify_install(self.target, self.payload)['complete'])

    def test_running_game_rejected_before_download_and_after_download(self):
        before = self.snapshot()
        with patch.object(installer.live, 'status', return_value={'attached': True}), \
                patch.object(fsr4build, 'fetch') as fetch:
            result = asyncio.run(self.service.set_fsr4_build(str(self.target), TEST_BUILD_ID))
            self.assertFalse(result['ok'])
            fetch.assert_not_called()
        with patch.object(installer.live, 'status', side_effect=[{}, {'attached': True}]):
            self.assertFalse(self.enable()['ok'])
        self.assertEqual(before, self.snapshot())

    def test_unmanaged_install_rejected(self):
        (self.target/MANIFEST_NAME).unlink()
        before = (self.target/FFX_UPSCALER_DLL).read_bytes()
        self.assertFalse(self.enable()['ok'])
        self.assertEqual(before, (self.target/FFX_UPSCALER_DLL).read_bytes())

    def test_manifest_write_failure_rolls_back_dll_and_ini(self):
        before = self.snapshot()
        real_copy = installer.atomic_copy
        def fail_once(source, destination):
            if Path(source).name == 'new.json':
                raise OSError('simulated disk failure')
            real_copy(source, destination)
        with patch.object(installer, 'atomic_copy', side_effect=fail_once):
            self.assertFalse(self.enable()['ok'])
        self.assertEqual(before, self.snapshot())

    def test_retired_build_still_verifies_and_reinstalls(self):
        """Retiring an entry must not orphan the installs made while it was current.

        The bytes are still the bytes this plugin put there, so verify has to pass,
        reinstall has to preserve them, and the status has to say they can be
        replaced rather than reporting an unknown file.
        """
        retired_dll = self.root/'retired.dll'
        retired_dll.write_bytes(b'retired upscaler DLL')
        retired = dict(self.build, id='retired-build', retired=True,
                       successor=TEST_BUILD_ID,
                       file_sha256=hashlib.sha256(retired_dll.read_bytes()).hexdigest(),
                       file_bytes=retired_dll.stat().st_size)
        with patch.object(fsr4build, 'FSR4_RETIRED_BUILDS', [retired]):
            installer.install_fsr4_build(self.target, retired_dll, retired, None, True)
            self.assertTrue(installer.verify_install(self.target, self.payload)['complete'])
            status = installer.fsr4_status(self.target)
            self.assertEqual(status['build']['id'], 'retired-build')
            self.assertTrue(status['build']['retired'])
            self.assertEqual(status['build']['successor'], TEST_BUILD_ID)
            self.assertTrue(status['needs_replacement'])
            installer.install(self.target, self.payload)
            self.assertEqual((self.target/FFX_UPSCALER_DLL).read_bytes(),
                             retired_dll.read_bytes())
            self.assertEqual(installer.read_manifest(self.target)['fsr4_build']['id'],
                             'retired-build')

    def test_retired_build_cannot_be_chosen_again(self):
        retired = dict(self.build, id='retired-build', retired=True,
                       successor=TEST_BUILD_ID)
        with patch.object(fsr4build, 'FSR4_RETIRED_BUILDS', [retired]), \
                patch.object(fsr4build, 'fetch') as fetch:
            result = asyncio.run(self.service.set_fsr4_build(str(self.target), 'retired-build'))
            self.assertFalse(result['ok'])
            fetch.assert_not_called()

    def test_retired_build_is_not_offered(self):
        retired = dict(self.build, id='retired-build', retired=True,
                       successor=TEST_BUILD_ID)
        with patch.object(fsr4build, 'FSR4_RETIRED_BUILDS', [retired]):
            offered = [build['id'] for build in fsr4build.builds()]
            self.assertIn(TEST_BUILD_ID, offered)
            self.assertNotIn('retired-build', offered)
            # ...but it is still findable, which is what verify and reinstall need.
            self.assertEqual(fsr4build.find('retired-build')['id'], 'retired-build')
            with self.assertRaisesRegex(ValueError, 'retired'):
                fsr4build.fetch(retired, self.root/'cache')


class PinBuildTests(unittest.TestCase):
    """The pinning helper: what it prints has to be pasteable, and true."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        fsr4build._digests.clear()
        self.dll_bytes = b'a community build that is not pinned yet'
        self.archive = self.root / 'FSR_4.1.1d_INT8.7z'
        self.archive.write_bytes(b'archive bytes')
        self.addCleanup(patch.stopall)

    def extract(self, archive, target, logger=None):
        target.mkdir(parents=True, exist_ok=True)
        (target / FFX_UPSCALER_DLL).write_bytes(self.dll_bytes)

    def run_helper(self, *argv, extract=True):
        """Run main() with the archiver replaced; returns what it printed."""
        patches = [patch.object(sys, 'argv',
                                ['pin_fsr4_build.py', str(self.archive), *argv])]
        if extract:
            patches.append(patch.object(pin_fsr4_build.payload, 'extract_archive',
                                        side_effect=self.extract))
        for started in patches:
            started.start()
        out = io.StringIO()
        with redirect_stdout(out):
            pin_fsr4_build.main()
        return out.getvalue()

    def entry_from(self, *argv):
        """The dict the helper printed, read back the way a paste would."""
        text = self.run_helper(*argv)
        return ast.literal_eval(text[text.index('{'):text.rindex('}') + 1])

    def test_what_it_prints_is_a_pasteable_working_entry(self):
        entry = self.entry_from('--id', '4.1.1d')
        self.assertEqual(entry['id'], '4.1.1d')
        self.assertTrue(entry['sources'][0]['local'])
        self.assertEqual(entry['sources'][0]['asset'], self.archive.name)
        self.assertEqual(entry['sources'][0]['archive_sha256'],
                         hashlib.sha256(self.archive.read_bytes()).hexdigest())
        self.assertEqual(entry['file'], FFX_UPSCALER_DLL)
        self.assertEqual(entry['file_sha256'],
                         hashlib.sha256(self.dll_bytes).hexdigest())
        self.assertEqual(entry['file_bytes'], len(self.dll_bytes))
        self.assertEqual(entry['reaches_fsr4_by'], 'int8')
        # A pin is only worth anything if the DLL it names is then recognised.
        dll = self.root / FFX_UPSCALER_DLL
        dll.write_bytes(self.dll_bytes)
        with patch.object(fsr4build, 'FSR4_BUILDS', [entry]):
            self.assertEqual(fsr4build.identify(dll)['id'], '4.1.1d')

    def test_an_older_build_is_pinned_as_the_upgrade_route(self):
        self.assertEqual(self.entry_from('--id', '4.0.2d')['reaches_fsr4_by'], 'upgrade')

    def test_the_dll_inside_an_archive_is_not_what_gets_pinned(self):
        # The extracted DLL is the tempting thing to feed it, and the one thing a
        # pin cannot be: fetch unpacks an archive, so these bytes would name a
        # build that never installs.
        dll = self.root / FFX_UPSCALER_DLL
        dll.write_bytes(self.dll_bytes)
        with patch.object(sys, 'argv', ['pin_fsr4_build.py', str(dll)]):
            with self.assertRaises(SystemExit) as caught:
                pin_fsr4_build.main()
        self.assertIn('not an archive', str(caught.exception))

    def test_a_release_source_is_printed_when_it_has_one(self):
        entry = self.entry_from('--id', '4.1.1d', '--repo', 'owner/name',
                                '--tag', 'fsr4-4.1.1d')
        self.assertNotIn('local', entry['sources'][0])
        self.assertEqual(entry['sources'][0]['repo'], 'owner/name')
        self.assertEqual(entry['sources'][0]['tag'], 'fsr4-4.1.1d')

    def test_a_relabel_of_a_pinned_build_is_refused(self):
        bundled = dict(fsr4build.BUNDLED_BUILD, file_bytes=len(self.dll_bytes),
                       file_sha256=hashlib.sha256(self.dll_bytes).hexdigest())
        with patch.object(fsr4build, 'BUNDLED_BUILD', bundled):
            with self.assertRaises(SystemExit) as caught:
                self.run_helper()
        self.assertIn('already pinned', str(caught.exception))

    def test_an_archive_that_is_already_pinned_is_refused(self):
        pinned = {'id': '4.1.1x', 'sources': [
            {'local': True, 'asset': 'x.7z',
             'archive_sha256': hashlib.sha256(self.archive.read_bytes()).hexdigest()}]}
        with patch.object(pin_fsr4_build, 'FSR4_BUILDS', [pinned]):
            with self.assertRaises(SystemExit) as caught:
                self.run_helper(extract=False)
        self.assertIn('already pinned', str(caught.exception))

    def test_an_archive_without_the_upscaler_in_it_says_so(self):
        def empty(archive, target, logger=None):
            target.mkdir(parents=True, exist_ok=True)
        with patch.object(pin_fsr4_build.payload, 'extract_archive', side_effect=empty):
            with self.assertRaises(SystemExit) as caught:
                self.run_helper(extract=False)
        self.assertIn('holds no', str(caught.exception))


if __name__ == '__main__':
    logging.disable(logging.CRITICAL)
    unittest.main()
