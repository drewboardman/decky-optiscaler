#!/usr/bin/env python3
"""Turn a downloaded FSR 4 archive into a `FSR4_BUILDS` entry.

A build is pinned by hash: the archive it arrived in and the DLL inside it. The
version resource is recorded but not relied on, because two files can report the
same version and not be the same library -- which is what the community respins
did, every one of them claiming the version the OptiScaler release bundles.

This prints those hashes in the shape `py_modules/optiscaler/constants.py`
wants, and nothing else is written: the archive stays where it is. It is given
the archive, not the DLL taken out of it, because an archive is what `fetch`
unpacks and verifies. Its other job is to say when the file is *not* a new build
-- if these bytes are a build that is already pinned, or the one the release
ships, the answer is "there is nothing to add" rather than a new entry that would
install the same DLL under a second name.

    python3 scripts/pin_fsr4_build.py ~/Downloads/FSR_4.1.1d_INT8.7z
    python3 scripts/pin_fsr4_build.py ~/Downloads/FSR4_INT8_4.1.1d.7z \\
        --id 4.1.1d --repo drewboardman/decky-optiscaler --tag fsr4-4.1.1d

Requires 7z, 7zz, 7za, 7zr or bsdtar: the same archivers the plugin unpacks
with, and the reason is the same (these packages use the BCJ2 filter).
"""

import re
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "py_modules"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import package  # noqa: E402  (what bin/ may hold is defined there, not here)
from optiscaler import fsr4build, payload  # noqa: E402
from optiscaler.constants import FFX_UPSCALER_DLL, FSR4_BUILDS  # noqa: E402

#: What a build arrives in. This is `package.ALLOWED_BIN_SUFFIXES` without the
#: `.asi`, which is the OptiPatcher plugin rather than a build: the table names an
#: archive because `fetch` unpacks one and takes the DLL out of what it produced.
ARCHIVE_SUFFIXES = (".7z", ".zip")

#: A version the community would put in a build's own id, e.g. `4.1.1d`.
VERSION = re.compile(r"\d+\.\d+\.\d+[a-z]?")
#: ...and the part of it that is a version number, since `reaches_fsr4_by` is
#: asked about the SDK version and the trailing letter is not part of it.
NUMBERS = re.compile(r"\d+\.\d+\.\d+")

USAGE = (
    f"usage: {Path(sys.argv[0]).name} ARCHIVE [--id ID] [--label LABEL] "
    "[--note NOTE] [--repo OWNER/NAME --tag TAG]"
)


def arguments(argv):
    """(archive, options) from the command line, or a usage error."""
    if not argv or argv[0] in ("-h", "--help"):
        raise SystemExit(USAGE)
    archive = Path(argv[0]).expanduser()
    if not archive.is_file():
        raise SystemExit(f"no such archive: {archive}")
    if archive.suffix.lower() not in ARCHIVE_SUFFIXES:
        # The DLL inside the archive is the tempting thing to feed this, and it is
        # the one thing that cannot be pinned: `fetch` unpacks an archive, so an
        # entry hashing a bare DLL would name a build that never installs.
        raise SystemExit(
            f"{archive.name} is not an archive. This pins the "
            f"{'/'.join(ARCHIVE_SUFFIXES)} a build arrived in, not the DLL taken "
            "out of it -- unpack that DLL into a game folder and there is nothing "
            "left to verify it against. Feed it the file as downloaded; if it "
            "arrived with no extension, rename it to the one it actually is."
        )
    options = {}
    rest = argv[1:]
    while rest:
        flag = rest.pop(0)
        if flag not in ("--id", "--label", "--note", "--repo", "--tag") or not rest:
            raise SystemExit(USAGE)
        options[flag[2:]] = rest.pop(0)
    if ("repo" in options) != ("tag" in options):
        raise SystemExit("--repo and --tag go together")
    return archive, options


def unpack(archive, into):
    """Extract `archive` and return the upscaler DLL inside it."""
    payload.extract_archive(archive, into)
    found = sorted(
        (p for p in Path(into).rglob(FFX_UPSCALER_DLL) if p.is_file()),
        key=lambda p: (len(p.parts), str(p)),
    )
    if not found:
        raise SystemExit(
            f"that archive holds no {FFX_UPSCALER_DLL} -- it is probably the usual "
            "OptiScaler release rather than a build of the SDK library"
        )
    if len(found) > 1:
        print(f"note: {len(found)} copies of {FFX_UPSCALER_DLL}; using the shallowest")
    return found[0]


def licence_files(root):
    """Anything in the archive that is terms rather than code."""
    wanted = ("licen", "notice", "copying", "eula", "readme", "about")
    return sorted(
        p.relative_to(root).as_posix()
        for p in Path(root).rglob("*")
        if p.is_file() and any(word in p.name.lower() for word in wanted)
    )


def version_of(build_id):
    """The version a build's own id names, as the tuple `reaches_fsr4_by` wants."""
    match = NUMBERS.search(build_id)
    if not match:
        return None
    return tuple(int(part) for part in match.group().split("."))


def source_text(archive, repo, tag):
    """The one source dict, indented for the table it is pasted into."""
    digest = payload.sha256(archive)
    if repo:
        members = [f'"repo": "{repo}"', f'"tag": "{tag}"']
        comment = []
    else:
        members = ['"local": True']
        comment = ['# Shipped in bin/, so there is no release to fetch it from']
    members += [f'"asset": "{archive.name}"', f'"archive_sha256": "{digest}"']
    body = "".join(
        [f"                {line}\n" for line in comment]
        + [f"                {line},\n" for line in members]
    )
    return "            {\n" + body + "            },"


def entry(archive, dll, build_id, label, note, repo, tag):
    """The `FSR4_BUILDS` member, as source text."""
    reaches = fsr4build.reaches_fsr4_by(version_of(build_id)) or "int8"
    return (
        "    {\n"
        f'        "id": "{build_id}",\n'
        f'        "label": "{label}",\n'
        f'        "note": "{note}",\n'
        '        "sources": [\n'
        f"{source_text(archive, repo, tag)}\n"
        "        ],\n"
        f'        "file": "{FFX_UPSCALER_DLL}",\n'
        f'        "file_sha256": "{payload.sha256(dll)}",\n'
        f'        "file_bytes": {dll.stat().st_size},\n'
        f'        "reaches_fsr4_by": "{reaches}",\n'
        "    },"
    )


def main():
    archive, options = arguments(sys.argv[1:])
    digest = payload.sha256(archive)
    match = VERSION.search(archive.stem)
    build_id = options.get("id") or (match.group() if match else archive.stem)

    known_archives = {
        source["archive_sha256"]: f'{build["id"]} ({source["asset"]})'
        for build in FSR4_BUILDS
        for source in build["sources"]
    }
    if digest in known_archives:
        raise SystemExit(
            f"this is the archive already pinned for {known_archives[digest]} -- "
            "nothing to add. (A renamed copy is still the same bytes.)"
        )

    with tempfile.TemporaryDirectory(prefix="pin-fsr4-") as temp:
        dll = unpack(archive, Path(temp))
        # identify() answers from the pinned table, so this is the same verdict
        # the panel would reach: known means these bytes are already offered.
        known = fsr4build.identify(dll)
        if known and known["known"]:
            raise SystemExit(
                f"the DLL inside is {known['label']!r}, a build that is already pinned "
                f"(id {known['id']}). Labelling the same bytes again would install the "
                "same library under a second name and change nothing."
            )
        print(f"archive   {archive.name} ({archive.stat().st_size / 1048576:.1f} MB)")
        print(f"          sha256 {digest}")
        print(f"dll       {FFX_UPSCALER_DLL} ({dll.stat().st_size:,} bytes)")
        print(f"          sha256 {payload.sha256(dll)}")
        same_size = [b["id"] for b in fsr4build.builds()
                     if b["file_bytes"] == dll.stat().st_size]
        if same_size:
            print(f"          same size as {', '.join(same_size)} but different bytes: a")
            print("          near-copy rather than those bytes, so check what it claims to be")
        else:
            print("          no pinned build has this size, so it is not a relabel of one")
        terms = licence_files(Path(temp))
        if terms:
            print("\nShipped alongside it (read before redistributing):")
            for name in terms:
                print(f"  {name}")
        body = entry(archive, dll, build_id,
                     options.get("label") or f"{build_id} (INT8, RDNA 2)",
                     options.get("note") or "Pinned by hash.",
                     options.get("repo"), options.get("tag"))

    print("\nPaste into FSR4_BUILDS in py_modules/optiscaler/constants.py:\n")
    print(body)
    if not options.get("repo"):
        allowed = ", ".join(package.ALLOWED_BIN_SUFFIXES)
        print(
            f"\nThen: copy the archive into bin/ as {archive.name} and commit it. bin/\n"
            f"takes {allowed}, and a build pinned here but missing from bin/ fails at\n"
            "install time -- the selftest reports that rather than letting it ship. Run:\n"
            "  python3 scripts/selftest.py && python3 scripts/test_fsr4.py"
        )


if __name__ == "__main__":
    main()