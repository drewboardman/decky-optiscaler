# Steam Deck FSR 4

Close the game, install OptiScaler through the plugin if needed, and select
**FSR 4 — Steam Deck** under Basic → Override upscaler with. Nothing is
downloaded: the archive ships inside the plugin (`bin/FSR4_4.1.2_INT8.zip`), so
setting up a second game is a copy rather than another transfer. Validation
failure leaves the previous DLL and settings intact.

This option installs AMD's own `amd_fidelityfx_upscaler_dx12.dll` from
[FSR SDK 2.4](https://github.com/GPUOpen-LibrariesAndSDKs/FidelityFX-SDK/releases/tag/v2.4.0),
which is FSR Upscaling **4.1.2**. Archive and DLL SHA-256 values are pinned in
the plugin, and the file reports `4.1.2.4555`. It carries both the full and the
Lite INT8 model; which one runs is decided inside the DLL. OptiScaler 0.9.4 has
no setting that overrides that choice, so there is nothing here to switch.

The plugin still bundles OptiScaler runtime **0.9.4**, including the original
SDK **4.1.1**. OptiScaler Client **1.0.7** is a separate management application;
it is not required or installed by this plugin.

## Settings and verification

The option selects the FidelityFX backend (`fsr31` for DX12), sets
`Fsr4ForceEnableInt8=true`, `UpscalerIndex=0`, and resets `Fsr4Update` and
`Fsr4Preset` to `auto`. DX11/Vulkan select the existing DX12 bridge backend.
INT8 initialization requires a fresh game launch. Per-game compatibility still
applies; the preset cannot add upscaler inputs to an unsupported game.

Launch the game and use its supported upscaler input (for example XeSS in the
Cyberpunk setup tested here). Enable the FSR watermark in OptiScaler to confirm
`FSR4-I8`; plain FSR3 indicates fallback. Setup identifies the installed patch,
while the watermark identifies the model actually running.

This is still experimental on the Steam Deck. AMD's 4.1.2 notes list RDNA 2 as
supported for discrete RX 6000 cards and for a set of Ryzen APUs — Strix Halo,
Strix Point, Gorgon Halo, Gorgon Point, Z2 A and Z2 Extreme. Van Gogh, the chip
in both Steam Deck models, is not named. Evaluate motion/ghosting, image quality
and base frame rate in the same scene before and after enabling.

It does not fix or enable FSR4 frame generation. You may keep FSR3 frame
generation with FSR4 upscaling; test stability separately.

## Pinning a build

`FSR4_BUILDS` is a table of builds identified by their bytes. The archive and the
DLL inside it are both pinned by SHA-256, so what an install puts in a game folder
is exactly the file that was reviewed, rather than whatever a URL serves on the
day it is fetched. The version resource is recorded but not trusted: two files can
report the same version and not be the same library.

A build with no public release is carried in `bin/` instead, as a source marked
`"local": True`. `fetch` unpacks it out of the install rather than downloading
anything, and the archive digest is checked exactly as a download's is. The
shipped file is never moved or deleted, so a copy that has been altered fails the
same way a bad download does. `bin/` accepts `.7z` and `.zip` archives, which
`scripts/package.py` enforces.

`scripts/pin_fsr4_build.py ARCHIVE` prints the entry to paste, with the archive
and DLL SHA-256, the DLL's size and the setting that reaches FSR 4. It refuses
the two cases where there is nothing to add: bytes already pinned, and the
release's own build under a new name. Run `scripts/selftest.py` afterwards — it
reports a build that is pinned but missing from `bin/`, which would otherwise
fail at install time.

## Replacing a retired build

A build the plugin stops offering moves to `FSR4_RETIRED_BUILDS` instead of
disappearing from it. Its bytes stay recognised, so an install made while it was
current keeps verifying, keeps surviving a reinstall, and can be reported in
Setup next to the build that replaces it. Dropping the entry outright would turn
that install into "Unrecognised FSR 4 build" and make reinstall refuse over a
build it could no longer find.

The 4.1.1b community build is now one of those: recognised, not offered, and
reported as replaceable. Setup names AMD's build beside it, and choosing that
replaces the DLL while keeping the upscaler and frame generation settings.

## Switching back

Choose FSR 3.X or another upscaler in Basic settings to change the active backend.
The installed build stays in place for later use. To go back to the one the
OptiScaler release ships (SDK 4.1.1), close the game and choose **Restore bundled
upscaler** in Setup. This keeps settings intact; INT8 configured by hand or
retained after restore is labelled **FSR 4 INT8 (manual)**.

Reinstall preserves a verified build. If that DLL is missing or altered, reinstall
stops with repair instructions instead of silently replacing it. Select the Steam
Deck option again to repair it, or restore the bundled DLL. Uninstall restores the
game's original backed-up files, not the OptiScaler SDK.

Any build added to the table should have its source and hashes reviewed first.
Older 4.0.2 variants are outside this feature's scope.
