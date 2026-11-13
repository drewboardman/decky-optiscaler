# Changelog

Newest first. Each release ships `Decky OptiScaler.zip` for Decky Loader's
*Install from URL* (Developer mode), and bundles **OptiScaler 10.0.0-pre1**.

## [Unreleased]

## [0.8.1] - 2026-11-13

### Added

- **HelixSR is detected and marked in the FSR 4 panel.** HelixSR runs NVIDIA's
  DLSS network — or FSR 4, from 3.x — on an AMD GPU by taking over what the game
  or OptiScaler asks for, so while it is installed the build shown in this plugin
  is not what renders. It is now reported in yellow with a note saying so, and
  the build picker says plainly that switching does nothing while HelixSR is in
  place. Both routes are recognised: HelixSR's own installer (its
  `helixsr-install.json` marker and, up to 1.x, `helixsr.ini`) and the OptiScaler
  route (a `HelixSR/` folder beside `OptiScaler.ini`, with `FfxDx12Path` or
  `FfxDx12SRPath` pointed into it). This plugin still neither installs nor
  removes HelixSR, and a leftover folder with the ini pointing elsewhere is not
  reported as an install.

### Fixed

- The changelog header still said this release bundles OptiScaler 0.9.4.

## [0.8.0] - 2026-11-13

### Removed

- **AMD's driver FSR libraries are no longer bundled.** `amdxcffx64.dll` and
  `amdvkffx64.dll` were 39 MB of the download, and the only thing they enabled on a Deck
  was v10's model selector — whose Lite model measured worse than the community RDNA 2 build
  in both image quality and frame rate. The release drops from 111.6 MB to about 73 MB.
- With them gone the SDK upscaler in `<game>/OptiScaler/` is the only FSR 4 source, so the
  Deck preset's `auto` has nothing else to resolve to. `Fsr4Model` and `Fsr4GpuSupport` remain
  in Advanced as part of v10's ini, but select nothing without a driver library beside them.

## [0.0.7-steamdeck.9] - 2026-11-13

### Fixed

- **The compatibility list is read whole again.** One row in the wiki table — Metro
  Exodus: Enhanced Edition — was saved without its leading pipe, which the parser
  took as the end of the table: every row after it was dropped. That is 297 of 695
  games, among them Monster Hunter Wilds, every Resident Evil entry and Stalker 2,
  each reported to the user as "no wiki entry matched". A line that still ends the
  way a row ends and carries enough separators to be one is now read as the row it
  is, and prose carrying a pipe still is not.
- The two mod tables on that page have their own shape — no OptiPatcher column.
  Read by column position, their notes were taken for patcher support, so every
  game listed there claimed OptiPatcher, and their images column was served as the
  entry's notes to both the user and the plan builder. Columns now come from each
  table's own header row.

## [0.0.7-steamdeck.8] - 2026-11-13

### Changed

- The README and the Steam Deck page describe what the plugin actually ships now: the
  bundled runtime is OptiScaler 10.0.0-pre1 with its `OptiScaler/` folder, the Deck preset
  installs the community RDNA 2 build and leaves OptiScaler's model selector at `auto`, and
  live in-game control is off until the ASI is re-vendored.
- Documented the Lite measurement: it loads (`FSR4L-i8 Upscale 4.1.2`) and is worse than the
  build it replaced on Van Gogh. `Fsr4Model` / `Fsr4GpuSupport` stay in Advanced for anyone who
  wants to compare.

No code changes in this release.

## [0.0.7-steamdeck.7] - 2026-11-10

### Fixed

- **The Steam Deck preset is back on the community RDNA 2 build.** 0.0.7-steamdeck.6
  forced v10's Lite model (`Fsr4GpuSupport=4`, `Fsr4Model=3`). It does load on a
  Deck — the watermark reads `FSR4L-i8 Upscale 4.1.2` — but it is slower and looks
  worse than the 4.1.1b build it replaced, so the preset now installs that build
  and leaves `Fsr4GpuSupport` and `Fsr4Model` at `auto`.
- 0.0.7-steamdeck.6 is withdrawn. Both model keys remain in the schema, so Lite is
  still reachable from Advanced for anyone who wants to try it.

### Known limitations

- **Live in-game control is off in this build.** The ASI is compiled against a copy
  of the runtime's structs that is still 0.9.4; installing it into a v10 process
  would write through the old offsets. It returns once re-vendored.
- Whether `auto` resolves to the RDNA 2 build's own INT8 path or to the driver's
  model is unverified on device — the watermark distinguishes them.

## [0.0.7-steamdeck.6] - 2026-11-10

### Changed

- **The bundled runtime is OptiScaler v10** (the dated nightly
  `OptiScaler_v10.0.0-pre1_20261110`), pinned by hash like any other artifact.
  v10 keeps its libraries in `<game>/OptiScaler/` instead of beside the
  executable, and the installer, manifest, backups and verification follow it
  there — including a fix for backups that used to be flattened to a filename and
  restored to the game root.
- **The Steam Deck preset is FSR 4 Lite.** It writes `Dx12Upscaler=ffx`,
  `Dx11Upscaler=ffx_12`, `VulkanUpscaler=ffx_12`, `Fsr4GpuSupport=4` and
  `Fsr4Model=3`. AMD's driver FSR libraries ship with the plugin because v10 loads
  the Lite model from them, and the OptiScaler release does not contain them.
- The option schema is regenerated from v10's own ini: 355 options across 37
  sections, `fsr31` renamed to `ffx`, and `Fsr4Update` / `Fsr4ForceEnableInt8`
  replaced by `Fsr4GpuSupport` / `Fsr4Model`. Presets, automatic mode and the FSR
  version helper no longer write the removed keys.
- The community 4.1.1b build is still selectable in the FSR 4 panel. It is no
  longer the preset, because Lite should reach FSR 4 with AMD's own model.

### Known limitations

- **Live in-game control is off in this build.** The ASI is compiled against a
  copy of the runtime's structs that is still 0.9.4; installing it into a v10
  process would write through the old offsets. It returns once re-vendored.
- FSR 4 Lite on Van Gogh is still unverified on device — this build is the first
  one that can test it.

## [0.0.7-steamdeck.5] - 2026-11-10

### Fixed

- **The Steam Deck preset is back on the RDNA 2 build.** In 0.0.7-steamdeck.4 it
  pointed at AMD's own 4.1.2, which does not reach FSR 4 on Van Gogh: with that
  file in place, OptiScaler's FFX upscaler list reported FSR 3.1.6 and no FSR 4
  entry at all, so the preset installed something the Deck cannot use. The DLL
  does load — FSR 3.1.6 exists only in SDK 2.4 — it just offers no ML path on
  this chip, which AMD's own support notes bear out.
- 4.1.1b is offered again, and both builds now ship in `bin/`, so either one is a
  one-tap switch with no download and nothing to fetch from a third-party release.
- 4.1.2 is still in the FSR 4 panel, labelled with what it actually does on a
  Deck rather than recommended as its replacement.
- The retired-build table is empty again. The machinery stays: it is what keeps a
  dropped build's installs verifiable.

## [0.0.7-steamdeck.4] - 2026-11-10

> Superseded by 0.0.7-steamdeck.5 — the preset it shipped does not reach FSR 4 on
> a Steam Deck.

### Added

- A pinned FSR 4 build may name a `"local"` source instead of a release, in which
  case the archive is read out of the plugin's own `bin/` rather than downloaded.
  That is the only way to offer a build with no public release to point at: a
  community drop posted as a chat-server attachment has no stable URL, and its
  digest is still verified before anything is unpacked.
- `scripts/pin_fsr4_build.py`, which turns a downloaded archive into the
  `FSR4_BUILDS` entry to paste — and refuses when the bytes are already pinned or
  are the build the OptiScaler release ships, since neither needs a second name.
- `FSR4_RETIRED_BUILDS`: a build this plugin stops offering stays identifiable by
  its bytes. Without it every existing install of that build would read as an
  unrecognised file, verify would call those bytes a problem on every check, and
  reinstall would refuse over a build it could not find.

### Changed

- **The Steam Deck preset installs AMD's own upscaler.** FSR Upscaling 4.1.2 from
  FSR SDK 2.4 now ships in `bin/FSR4_4.1.2_INT8.zip`, verified against a pinned
  digest before it is unpacked, so reaching FSR 4 needs no download. 4.1.2 supports
  RDNA 2 itself and carries both the full and the Lite INT8 model in one DLL.
- The community RDNA2 respin and both of its mirrors are gone, along with the
  anti-cheat caveat that came with redistributing a modified game DLL. `4.1.1b`
  remains recognised and is reported as replaceable; Setup offers 4.1.2 next to it.
- `bin/` also accepts `.zip`, because community builds are published as both 7z
  and zip. The stray-file check in `scripts/package.py` is otherwise unchanged.
- The selftest reports a build pinned to a local source that is not in `bin/`,
  instead of leaving it to fail on the Deck at install time. It also checks that
  a retired build is not offered and that its successor is.

## [0.0.7-steamdeck.3] - 2026-09-24

Prerelease adding Heroic support to the Steam Deck FSR 4 test build.

### Added

- Detect Epic, GOG and Amazon Windows games installed through native or Flatpak
  Heroic, including custom game install locations and Heroic Steam shortcuts.
- Reuse the executable-folder picker and add per-game Heroic DLL configuration.
  Quit Heroic before applying it. Existing environment settings are preserved;
  prior overrides can be restored and are restored when removing OptiScaler.

### Validation and compatibility

- Updating the plugin does not reinstall existing game files or reset game settings.
  Heroic settings are changed only through its setup action.
- Heroic discovery/settings fixtures and UI controls are tested. Actual Steam Deck
  Flatpak gameplay and live-control validation are still pending.
- Release selftests use fixed wiki responses instead of depending on changing
  online entries. The assertions for matching and background refresh remain enabled.
- The bundled OptiScaler version remains 0.9.4. This build retains the FSR 4 changes
  from test 2, listed below.

## [0.0.7-steamdeck.2] - 2026-09-18

### Added

- **FSR 4.1.1b — Steam Deck** in the Basic upscaler dropdown. Downloads the pinned
  community RDNA2 upscaler and applies INT8 settings together while the game is
  stopped. Frame generation is unchanged. Setup identifies the installed build
  and offers restoration of the bundled SDK.

### Fixed

- Verification recognizes the selected community DLL by hash; reinstall preserves it.
- DLL replacements use atomic file replacement with rollback on errors and reject
  unmanaged installs or games detected running.
- The schema offers all six FSR4 quality presets from the reference INI.
- Selecting an FSR version on RDNA2 no longer forces the incompatible upgrade path.

## [0.0.6] - 2026-08-28

Everything from the `0.0.5.x-testing` prereleases, as one release.

### Added

- Non-Steam games can be set up. Their folder is taken from the shortcut's
  target, since Steam reports no install folder for them.
- Games whose wiki entry requires
  [REFramework](https://github.com/praydog/REFramework) say so on the setup
  checklist and link the right build. Installing it for you is disabled for
  now, until I can gather more information to get it fully working.

### Fixed

- A non-Steam game's launch options are read from `shortcuts.vdf`, so removing
  OptiScaler no longer wipes them.
- Settings are read only from the install method this plugin actually performs.
  Monster Hunter Wilds would not boot because of this.
- Settings hedged by an "if", a "try", an "e.g." or a "desired" are reported
  rather than applied. Resident Evil 2 was getting 2× output scaling it never
  asked for.
- Setup names the OptiScaler overlay's new shortcut key when an entry moves it
  off Insert.
- Wiki pages with brackets in the name download again — Resident Evil, Dead
  Space (2023) and Elden Ring were affected. Bundled list regenerated.

[0.0.6]: https://github.com/danielcamilo1/decky-optiscaler/releases/tag/v0.0.6

## [0.0.5.3-testing] - 2026-08-27

Prerelease on the `testing` branch.

### Added

- Non-Steam games can be set up. Their folder is taken from the shortcut's
  target, since Steam reports no install folder for them.

### Changed

- Automatic REFramework setup is disabled for now, until I can gather more
  information to get it fully working. The games that need it still say so and
  link the right build, and REFramework installed by 0.0.5.1/0.0.5.2-testing can
  still be removed.

### Fixed

- A non-Steam game's launch options are read from `shortcuts.vdf`, so removing
  OptiScaler no longer wipes them.

## [0.0.5.2-testing] - 2026-08-24

Prerelease.

### Fixed

- Monster Hunter Wilds would not boot: settings were being read from install
  methods other than the one performed.
- Resident Evil 2 got 2× output scaling it never asked for. Settings hedged by
  an "if", a "try", an "e.g." or a "desired" are reported, not applied.
- Setup names the OptiScaler overlay's new shortcut key when an entry moves it
  off Insert.

## [0.0.5.1-testing] - 2026-08-24

Prerelease. REFramework auto-install — **disabled in 0.0.5.3-testing**.

### Added

- The nine compatibility-list games that need REFramework are detected, and the
  build, the `dinput8` override and `PDPerfPlugin.dll` are stated on the
  checklist.

### Fixed

- Wiki pages with brackets in the name download again — Resident Evil, Dead
  Space (2023) and Elden Ring were affected. Bundled list regenerated.

## [0.0.5] - 2026-08-23

### Added

- Removing OptiScaler asks what to do with the Steam launch options: restore
  what was there, remove only the OptiScaler override, or change nothing. The
  answer can be remembered.
- A Settings tab on the main page: remembered answers, the switch that stops
  answers being kept, and the state of the compatibility list.
- A copy of the compatibility list ships with the plugin, so an offline Deck
  still matches games.

### Changed

- The compatibility list is read from cache and refreshed in the background,
  instead of a network timeout in front of every question.

### Fixed

- Launch options are read from three sources, not just
  `SteamClient.Apps.GetAppLaunchOptions`, which some client builds do not have.
- A wiki that will not download is no longer reported as "your game is not on
  the list", and there is a **Try again** button.
- A stalled connection is retried over IPv4.
- The last-resort unverified TLS context no longer reads the system trust store.

[0.0.5]: https://github.com/danielcamilo1/decky-optiscaler/releases/tag/v0.0.5

## [0.0.4] - 2026-08-21

### Added

- The exact FSR version the running game built, rather than just the backend id.
- A second dropdown for which FSR version to run. Applies without a restart.
- Both frame rates while frame generation is on: what the game renders and what
  reaches the screen.
- A live-control readout that says why a number is missing, and a warning when a
  game's in-game plugin is out of date.

### Fixed

- A dropdown could keep a name its option list no longer used.
- Asking for FSR 4 could silently give you FSR 3.
- A game on the SD card reported itself as "writing to a different folder".
- The newest FSR version was named after the reference INI's build, not the
  bundled one.

[0.0.4]: https://github.com/danielcamilo1/decky-optiscaler/releases/tag/v0.0.4

## [0.0.3] - 2026-08-20

### Fixed

- The upscaler dropdown lagged one change behind after reopening the panel.
- The FidelityFX FG version control disappeared on games reporting one
  generator.

[0.0.3]: https://github.com/danielcamilo1/decky-optiscaler/releases/tag/v0.0.3

## [0.0.2] - 2026-08-20

### Fixed

- A control could display a value it was not set to.
- Picking the third FidelityFX frame generator did nothing.
- Settings the config writer refused are reported instead of left on screen.
- Re-reading the config could undo an edit or blank the panel.
- The live upscaler switch works for DX11 games.

[0.0.2]: https://github.com/danielcamilo1/decky-optiscaler/releases/tag/v0.0.2

## [0.0.1] - 2026-08-20

First public release.

### Added

- Per-game install, into a folder scored automatically and overridable by hand.
  Steam libraries including the SD card, plus any folder as a custom library.
- Automatic setup from the OptiScaler
  [Compatibility List](https://github.com/optiscaler/OptiScaler/wiki/Compatibility-List),
  as a checklist that names the wiki field behind every line before writing it.
- Basic settings (four controls) and Advanced (all 288 options across 34
  sections), generated from the shipped `OptiScaler.ini` and preserving its
  comments.
- Live in-game control of frame generation, the FidelityFX FG version and the
  upscaler, with a frame rate readout, via a bundled ASI plugin.
- Quick Access panel: the running game's live controls and a filtered game list.
- Files an install would overwrite are backed up and restored on uninstall.
- `OptiScaler.log` parsing, bundled
  [OptiPatcher](https://github.com/optiscaler/OptiPatcher), and an **OptiScaler
  Settings** entry in the Steam library context menu.

[0.0.1]: https://github.com/danielcamilo1/decky-optiscaler/releases/tag/v0.0.1
