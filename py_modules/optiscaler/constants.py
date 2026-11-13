"""Shared constants for the Decky OptiScaler plugin."""

OPTISCALER_VERSION = "10.0.0-pre1"
#: The nightly this is pinned to. These are dated tags with a fixed asset name,
#: so this stays a pinned artifact rather than a moving target — and the date is
#: part of the name on purpose, so "which build is in this release" is answerable
#: without trusting a "latest" pointer.
PAYLOAD_ARCHIVE = "OptiScaler-10.0.0-pre1_20261110.7z"
PAYLOAD_SHA256 = "a744775492ec0c0b0df9804b3b83918aea8b9deb56b3084b1efb81731242c69d"

#: The live-control ASI is compiled against the copy of the runtime's structs in
#: `asi/optiscaler_ref/`. That copy is 0.9.4, and v10 moved members around, so an
#: ASI built from it would write through the old offsets inside a v10 process —
#: which is a corruption bug, not a missing feature. Withheld until it is
#: re-vendored; `install_live` already reports that this build ships none.
LIVE_ASI_ENABLED = False

# HelixSR (https://github.com/lonewolf0622/HelixSR) is a separate project: it runs
# NVIDIA's DLSS network — or from 3.x, AMD's FSR 4 network — on AMD GPUs by
# replacing what the game or OptiScaler calls for upscaling. This plugin neither
# installs nor removes it, but it lands in the same folder and explains why the
# FSR 4 panel can disagree with what the game is actually running.
HELIXSR_DIR = "HelixSR"
#: Written by HelixSR's own installer when it replaces the game's FSR 3.1 DLL.
HELIXSR_MARKER = "helixsr-install.json"
#: Written beside it by HelixSR 1.x; 3.x drops it.
HELIXSR_INI = "helixsr.ini"
#: HelixSR's copy of the OptiScaler settings it changed, kept for its revert.
HELIXSR_SETTINGS_BACKUP = "OptiScaler.ini.helixsr-backup"

INI_NAME = "OptiScaler.ini"
LOG_NAME = "OptiScaler.log"
# Written by this plugin so an install can be recognised later with certainty.
MANIFEST_NAME = ".decky-optiscaler.json"
# Anything OptiScaler would overwrite is moved here instead, and moved back on
# uninstall. Kept as a visible folder so it is obvious what happened.
BACKUP_DIR = "decky_optiscaler_backup_files"
# The same idea for the one thing that is not a file in this folder: the Steam
# launch options the game had before OptiScaler went in. Only the frontend can
# read them out of Steam, so they are handed here and written verbatim, and
# removing OptiScaler can then offer to put them back.
LAUNCH_RECORD_NAME = "decky_optiscaler_previous_launch_options.txt"

# OptiPatcher (https://github.com/optiscaler/OptiPatcher) is a separate ASI from
# the OptiScaler project. It patches supported games so their DLSS/DLSS-FG
# inputs are exposed without DXGI spoofing, which some games - Red Dead
# Redemption 2, for one - need before OptiScaler can do anything useful. It is
# shipped as a rolling release, so this records the build bundled here.
OPTIPATCHER_NAME = "OptiPatcher.asi"
OPTIPATCHER_ARCHIVE = "OptiPatcher.asi"
OPTIPATCHER_SHA256 = "1324e6d131410fd43b721d684e7fd950c4f33c4c31a1db475f3d134a0ef3faeb"
OPTIPATCHER_VERSION = "rolling (2026-08-18)"

# REFramework (https://github.com/praydog/REFramework) is a separate mod, not
# part of OptiScaler. A handful of RE Engine games — the Resident Evil titles,
# Devil May Cry 5, Monster Hunter Wilds, PRAGMATA — cannot host OptiScaler at
# all without it, because REF is what exposes the upscaler hooks OptiScaler
# attaches to. The compatibility list says so in prose ("Requires REFramework"),
# and until this the plugin read straight past it: the install succeeded, the
# launch options were set, and the game rendered exactly as it had before.
#
# Both builds ship the same single file, which is the whole reason installing it
# from here is safe to do automatically.
#
# **Automatic installation is withdrawn** as of 0.0.5.3-testing. Downloading a
# third-party engine hook and placing it in somebody's game folder on their
# behalf is a bigger promise than the rest of this plugin makes, and the two
# prereleases that did it turned up more ways for that to go wrong than it was
# worth. Nothing is deleted: detection, classification, the launch-options
# override, the status read and the removal path all stay exactly as they were
# and are still covered by the selftest, because the requirement is real and
# saying so is the useful half. What the flag switches off is the download —
# the plugin states what the game needs and where to get it, and the file is
# the user's to place. Setting this back to True restores the whole feature.
REFRAMEWORK_AUTO_INSTALL = False
# What the plan says instead, in the sentence the checklist builds around it.
REFRAMEWORK_WITHHELD = (
    "this plugin no longer downloads it for you"
)
REFRAMEWORK_DLL = "dinput8.dll"
REFRAMEWORK_REVISION = "reframework_revision.txt"
# What may be taken out of an REFramework archive at all: this writes into a
# folder full of somebody's game, and "extract the zip" is not a thing to do on
# trust.
REFRAMEWORK_FILES = [REFRAMEWORK_DLL, REFRAMEWORK_REVISION]
# ...but only the DLL is placed next to the executable. The nightly's own
# release notes are blunt about it — "do NOT extract any file other than
# dinput8.dll into your game folder, or your game may become unstable" — so the
# revision stamp stays in the download cache and is recorded in our manifest
# instead, which is where we wanted to read it from anyway.
REFRAMEWORK_INSTALL_FILES = [REFRAMEWORK_DLL]

# praydog's own nightly, which is now one unified build covering every game it
# supports — hence a single asset rather than the per-game ones the wiki text
# still describes.
REFRAMEWORK_NIGHTLY_URL = (
    "https://github.com/praydog/REFramework-nightly/releases/latest/download/REFramework.zip"
)
REFRAMEWORK_NIGHTLY_PAGE = "https://github.com/praydog/REFramework-nightly/releases/latest"

# The pd-upscaler branch, which the Resident Evil entries and DMC5 ask for by
# name. It is built per game, and PDPerfPlugin does not support the unified
# nightly above, so the two are genuinely different downloads rather than one
# being a newer version of the other. The official repo's artifact links expire,
# which is why the wiki points at this mirror.
REFRAMEWORK_PD_RELEASES = "https://api.github.com/repos/TheRazerMD/REFramework/releases"
REFRAMEWORK_PD_PAGE = "https://github.com/TheRazerMD/REFramework/releases"

# Which per-game asset each compatibility-list entry needs, by the entry's
# normalised key. Curated rather than guessed: the asset names are game codes
# ("RE2", "DMC5") that no amount of matching gets to from "Resident Evil 2
# (2019)", and installing the wrong game's REFramework build is a crash on
# launch. A game not in here reports that it could not be fetched and links the
# release page — it never falls back to a near-enough asset.
REFRAMEWORK_PD_ASSETS = {
    "devilmaycry5": "DMC5.zip",
    "dragonsdogmaii": "DD2.zip",
    "monsterhunterrise": "MHRISE.zip",
    "monsterhunterstories3twistedreflection": "MHSTORIES3.zip",
    "monsterhunterwilds": "MHWILDS.zip",
    "pragmata": "PRAGMATA.zip",
    "residentevil22019": "RE2.zip",
    "residentevil32020": "RE3.zip",
    "residentevil42023": "RE4.zip",
    "residentevil7biohazard": "RE7.zip",
    "residentevil8village": "RE8.zip",
    "residentevil9requiem": "RE9.zip",
}

# PureDark's UpscalerBasePlugin, which the pd-upscaler entries need alongside
# REFramework. It is on Nexus Mods behind a login, so it cannot be downloaded
# from here at all — the checklist names it, links it, and ticks when the file
# turns up next to the executable.
REFRAMEWORK_PD_PLUGIN = "PDPerfPlugin.dll"
REFRAMEWORK_PD_PLUGIN_NAME = "UpscalerBasePlugin 1.1.2"
REFRAMEWORK_PD_PLUGIN_URL = (
    "https://www.nexusmods.com/site/mods/502?tab=files&file_id=2293"
)

# The filenames OptiScaler may be installed under. Order matters: it is the
# order setup_linux.sh presents and the order we probe for existing installs.
PROXY_FILENAMES = [
    "dxgi.dll",
    "winmm.dll",
    "version.dll",
    "dbghelp.dll",
    "d3d12.dll",
    "wininet.dll",
    "winhttp.dll",
    "OptiScaler.asi",
]
DEFAULT_PROXY = "dxgi.dll"

# Where v10 keeps its own libraries: everything except the proxy dll and the ini
# lives in this folder instead of beside the executable. Paths in the lists below
# are relative to the game folder, so they carry the prefix.
PAYLOAD_SUBDIR = "OptiScaler"

# Support libraries copied into the game folder's OptiScaler/ directory.
PAYLOAD_FILES = [
    "OptiScaler/amd_fidelityfx_framegeneration_dx12.dll",
    "OptiScaler/amd_fidelityfx_framegeneration_vk.dll",
    "OptiScaler/amd_fidelityfx_loader_dx12.dll",
    "OptiScaler/amd_fidelityfx_loader_vk.dll",
    "OptiScaler/amd_fidelityfx_upscaler_dx12.dll",
    "OptiScaler/amd_fidelityfx_upscaler_vk.dll",
    "OptiScaler/dlssg_to_fsr3_amd_is_better.dll",
    "OptiScaler/libxell.dll",
    "OptiScaler/libxess.dll",
    "OptiScaler/libxess_dx11.dll",
    "OptiScaler/libxess_fg.dll",
    "OptiScaler/Streamlined_fetcher_windows.bat",
]
# D3D12_Optiscaler is inside PAYLOAD_SUBDIR now; Licenses stays at the root.
PAYLOAD_DIRS = ["Licenses"]

# AMD's driver FSR libraries (`amdxcffx64.dll`, `amdvkffx64.dll`) are deliberately
# not shipped. They are what v10's model selector drives — Lite in particular only
# exists in the Vulkan one — and Lite measured worse on a Deck than the community
# RDNA 2 build, so they bought 39 MB and nothing else. Without them the SDK
# upscaler in `OptiScaler/` is the only FSR 4 source, which is the one this plugin
# wants.

# Extra files OptiScaler or its helpers create at runtime; removed on uninstall.
RUNTIME_ARTIFACTS = [
    "OptiScaler.log",
    "fakenvapi.log",
    "dlssg_to_fsr3.log",
    "nvngx.ini",
]

# Directories that never contain a game's shipping executable.
EXE_DIR_BLACKLIST = {
    "engine",
    "_commonredist",
    "commonredist",
    "directx",
    "dotnet",
    "vcredist",
    "redist",
    "installers",
    "support",
    "tools",
    "dxsetup",
}

# Launcher executables that are not the real render target.
EXE_NAME_BLACKLIST = {
    "unitycrashhandler64.exe",
    "unitycrashhandler32.exe",
    "crashreportclient.exe",
    "crashhandler.exe",
    "uninstall.exe",
    "vcredist_x64.exe",
    "vcredist_x86.exe",
    "dxsetup.exe",
    "eossdk-win64-shipping.exe",
    "epicwebhelper.exe",
    "activationui.exe",
    "touchup.exe",
    "notification_helper.exe",
}

# FSR4 comes from amd_fidelityfx_upscaler_dx12.dll (the FidelityFX SDK), which
# IS bundled in the OptiScaler release — 4.1.1 in v0.9.4. amdxcffx64.dll is the
# alternative, driver-provided FSR4 source; OptiScaler only falls back to it when
# the SDK does not supply the effect. It is optional, not required.
FSR4_SUPPORT_FILES = ["amdxcffx64.dll", "amdxc64.dll"]

# The FidelityFX SDK dll that actually carries FSR4. FSR 4 arrived with the
# 4.0.2 build (FFX SDK 2.0), so that is the floor for "this file is a FSR 4
# library at all"; the INT8 model specifically needs 4.1.1, which is what
# OptiScaler's own menu asks for before it will offer the FSR 3.X/4 entry off
# the back of Fsr4ForceEnableInt8 (menu_common.cpp).
FFX_UPSCALER_DLL = "amd_fidelityfx_upscaler_dx12.dll"
FSR4_MIN_SDK_VERSION = (4, 0, 2, 0)
FSR4_INT8_MIN_SDK_VERSION = (4, 1, 1, 0)

# Places a user is likely to already have those DLLs.
FSR4_SOURCE_HINTS = [
    "fgmod",
    "fgmod/fsr4-rdna2-3",
    "fgmod/fsr4-rdna4",
    "fgmod/fsr4-rdna3-4-official-411",
    "fgmod/fsr4-rdna2-valve-411-pre10",
    "Downloads",
    "decky-optiscaler",
]

# The upscaler builds this plugin offers, both shipped in bin/ so that neither
# needs a download on a device that is often offline or tethered.
#
# Order is the order the panel lists them, and 4.1.1b is first on purpose: it is
# the build that reaches FSR 4 on Van Gogh. AMD's 4.1.2 does not. On a Deck its
# version list tops out at the FSR 3.1.6 it carries, with no FSR 4 entry at all,
# so OptiScaler has nothing to upgrade to and runs the analytical path instead.
# AMD's 4.1.2 notes cover RDNA 2 only as RX 6000 discrete cards and a set of
# Ryzen APUs — Z2 A is in that list, Van Gogh is not — and the community respin
# existed to get round exactly that check.
#
# Both are pinned by hash because the hash is what decides which bytes go into a
# game folder. The version resource only records what a file claims to be.
FSR4_BUNDLED_BUILD_ID = "bundled"
#: The build the release itself carries, identified by hash like any other. It is
#: FSR Upscaling 4.1.2 — the same bytes as AMD's SDK 2.4 DLL — so there is no
#: separate 4.1.2 entry below: the released build *is* 4.1.2.
FSR4_BUNDLED_FILE_SHA256 = (
    "aad4fccccb29084a655f9a4f9f613bd22c8c03fb4a0f8840148cc6543b4ccace"
)
FSR4_BUNDLED_FILE_BYTES = 57664272
FSR4_BUILDS = [
    {
        "id": "4.1.1b",
        "label": "4.1.1b (INT8, RDNA 2)",
        "note": "Community INT8 build with the RDNA2 ghosting fix. Reaches FSR 4 "
                "on Van Gogh through the INT8 override, which the released 4.1.2 "
                "build does not do there.",
        "sources": [
            {
                # Shipped in bin/, so there is no release to fetch it from
                "local": True,
                "asset": "FSR4_4.1.1b_INT8.7z",
                "archive_sha256": "66e9a818e0c914def7712c8dac06b08e64a64dbcfe77f3162d43ea6de93869ff",
            },
        ],
        "file": "amd_fidelityfx_upscaler_dx12.dll",
        "file_sha256": "0dd77d9c78d1ef9bc330cf4697ab3ffe24bc1aa7850e4130263dc922107fbd75",
        "file_bytes": 34013696,
        "reaches_fsr4_by": "int8",
    },
]

# Empty right now, and the machinery stays. Nothing is retired: 4.1.1b is offered
# again, because AMD's 4.1.2 turned out not to reach FSR 4 on Van Gogh and it was
# the only build that did. The table is kept because deleting an entry outright is
# what breaks installs — identify() would call those bytes "Unrecognised", verify
# would list them as a problem, and install() refuses to reinstall over a build it
# cannot find (installer.install). That distinction has now mattered twice.
FSR4_RETIRED_BUILDS = []


WIKI_RAW_BASE = "https://raw.githubusercontent.com/wiki/optiscaler/OptiScaler"
WIKI_HTML_BASE = "https://github.com/optiscaler/OptiScaler/wiki"
COMPAT_LIST_PAGE = "Compatibility-List.md"
COMPAT_CACHE_TTL = 24 * 60 * 60  # seconds

STEAM_ROOTS = [
    ".steam/steam",
    ".local/share/Steam",
    ".steam/root",
    ".var/app/com.valvesoftware.Steam/data/Steam",
]
