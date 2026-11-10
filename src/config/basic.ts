/**
 * Basic mode: a handful of controls that each drive several INI keys.
 *
 * OptiScaler's real configuration is split across keys that only make sense
 * together — an upscaler choice is a backend id plus an FSR4 flag, frame
 * generation is an input plus an output. Basic mode presents the combination.
 */

import type { ConfigValues, GpuInfo, LiveStatus, OptionChange } from "../types";
import { UPSCALER_LABELS } from "./labels";
import { AUTO, isAuto } from "./values";

export interface Preset {
  id: string;
  label: string;
  description?: string;
  /** Written when the preset is chosen. */
  changes: OptionChange[];
  /** Recognises the preset from the current INI values. */
  matches: (values: ConfigValues) => boolean;
}

const get = (values: ConfigValues, section: string, key: string) =>
  (values[section]?.[key] ?? AUTO).toLowerCase();
/** The build the Steam Deck preset installs.
 *
 * One name for it, because it is compared in three places — what the preset
 * asks the backend to install, and what the game folder reports afterwards. Two
 * string literals either side of that comparison drift apart silently the first
 * time the pinned build moves.
 *
 * Back to the community build: AMD's 4.1.2 offers no FSR 4 entry at all on Van
 * Gogh, so the preset that points at it installs a file the Deck cannot use. Both
 * builds stay offered in the FSR 4 panel; this is only which one the preset picks.
 */
export const FSR4_BUILD_ID = "4.1.1b";

const change = (section: string, key: string, value: string): OptionChange => ({
  section,
  key,
  value,
});

// -- Upscaler ---------------------------------------------------------------

/** Sets the same backend for every graphics API so the game gets it whichever it uses. */
function upscalerPreset(
  id: string,
  label: string,
  description: string,
  dx12: string,
  dx11: string,
  vulkan: string,
  fsr4Update?: boolean,
  int8?: boolean
): Preset {
  const changes = [
    change("Upscalers", "Dx12Upscaler", dx12),
    change("Upscalers", "Dx11Upscaler", dx11),
    change("Upscalers", "VulkanUpscaler", vulkan),
  ];
  if (fsr4Update !== undefined) {
    // v10 has no "allow FSR 4" flag: the version index and the model keys are
    // the whole choice. Asking for index 0 is asking for FSR 4.
    changes.push(change("FSR", "UpscalerIndex", fsr4Update ? "0" : "1"));
  }
  // `int8` used to write Fsr4ForceEnableInt8, which v10 removed. The Deck preset
  // spells the model keys out itself, so there is nothing to write here.
  void int8;
  return {
    id,
    label,
    description,
    changes,
    matches: (values) => {
      if (get(values, "Upscalers", "Dx12Upscaler") !== dx12) return false;
      if (fsr4Update === undefined) return true;
      const index = get(values, "FSR", "UpscalerIndex");
      return fsr4Update ? index === "0" : index !== "0";
    },
  };
}

export const UPSCALER_PRESETS: Preset[] = [
  {
    id: "auto",
    label: "Auto (leave the game alone)",
    description: "OptiScaler picks its own default for each API.",
    changes: [
      change("Upscalers", "Dx12Upscaler", AUTO),
      change("Upscalers", "Dx11Upscaler", AUTO),
      change("Upscalers", "VulkanUpscaler", AUTO),
      change("FSR", "Fsr4Update", AUTO),
      change("FSR", "Fsr4ForceEnableInt8", AUTO),
      change("FSR", "UpscalerIndex", AUTO),
    ],
    matches: (values) => isAuto(get(values, "Upscalers", "Dx12Upscaler")),
  },
  {
    // installer._replace_fsr4 owns the atomic DLL/settings write. This list
    // documents the preset for matching/validation; onEnableFsr4 applies it.
    id: "fsr4-int8",
    label: "FSR 4 Lite — Steam Deck",
    description: "Installs the RDNA 2 build and selects AMD's Lite model. Close the game first.",
    changes: [
      change("Upscalers", "Dx12Upscaler", "ffx"),
      change("Upscalers", "Dx11Upscaler", "ffx_12"),
      change("Upscalers", "VulkanUpscaler", "ffx_12"),
      // v10 replaced the allow-FSR-4 flag with two explicit choices: which GPU
      // support to claim, and which model to run. 4 + 3 is the Lite network on
      // an override, which is the only route to FSR 4 on Van Gogh.
      change("FSR", "Fsr4GpuSupport", "4"),
      change("FSR", "Fsr4Model", "3"),
      change("FSR", "UpscalerIndex", "0"),
      change("FSR", "Fsr4Preset", AUTO),
    ],
    matches: (values) =>
      get(values, "Upscalers", "Dx12Upscaler") === "ffx" &&
      get(values, "FSR", "Fsr4GpuSupport") === "4" &&
      get(values, "FSR", "Fsr4Model") === "3" &&
      get(values, "FSR", "UpscalerIndex") === "0",
  },
  upscalerPreset(
    "fsr4",
    "FSR 3.X/4",
    "OptiScaler's FidelityFX backend with FSR 4 turned on. Needs an RDNA 3 or RDNA 4 GPU.",
    "ffx", "ffx_12", "ffx_12", true, false
  ),
  upscalerPreset(
    "fsr31",
    "FSR 3.X",
    "The same backend running FSR 3.1. Works on any GPU — the safe choice on a Steam Deck.",
    "ffx", "ffx_12", "ffx_12", false, false
  ),
  upscalerPreset(
    "fsr22",
    "FSR 2.2.1",
    "Older FSR, most compatible.",
    "fsr22", "fsr22", "fsr22"
  ),
  upscalerPreset(
    "xess",
    "XeSS",
    "Intel's upscaler. Often the best image quality on AMD hardware.",
    "xess", "xess_12", "xess"
  ),
  upscalerPreset(
    "dlss",
    "DLSS",
    "Nvidia only — needs a real DLSS-capable GPU.",
    "dlss", "dlss", "dlss"
  ),
];

// -- Frame generation -------------------------------------------------------

function fgPreset(
  id: string,
  label: string,
  description: string,
  input: string,
  output: string
): Preset {
  return {
    id,
    label,
    description,
    changes: [
      change("FrameGen", "FGInput", input),
      change("FrameGen", "FGOutput", output),
    ],
    matches: (values) =>
      get(values, "FrameGen", "FGInput") === input &&
      get(values, "FrameGen", "FGOutput") === output,
  };
}

// Each preset is an FG Input and an FG Output together, and is named after the
// pair the way OptiScaler's own overlay names them, so that what is picked here
// is recognisable in the in-game FG Input / FG Output combos.
export const FG_PRESETS: Preset[] = [
  fgPreset(
    "fsrfg",
    "FSR FG",
    "FG Input “FSR 3.1 FG” into FG Output “FSR FG”. The most broadly compatible pair.",
    "fsrfg", "fsrfg"
  ),
  fgPreset(
    "xefg",
    "XeFG",
    "FG Input “FSR 3.1 FG” into FG Output “XeFG”. Supports 3X and 4X as well as 2X.",
    "fsrfg", "xefg"
  ),
  fgPreset(
    "nukems",
    "FSR3-FG via Nukem's",
    "FG Input “Nukem's DLSSG”. Uses the game's own DLSS-FG path — only for games that have it.",
    "nukems", "nukems"
  ),
  fgPreset(
    "dlssg",
    "DLSSG via Streamline",
    "FG Input “DLSSG via Streamline” into FG Output “FSR FG”. Only for games built on Streamline v2.",
    "dlssg", "fsrfg"
  ),
];

// -- The FFX frame generator ------------------------------------------------

/**
 * Which FidelityFX frame generator the FSR FG output runs.
 *
 * OptiScaler's overlay calls this "FFX FG" and changes it with a button
 * labelled "Change FG": it writes the index into its config and raises two
 * flags that make the FG context rebuild, which is the one part of frame
 * generation that genuinely does change mid-game. The list is not fixed — the
 * FFX SDK reports what it can offer to each game — so a running game is a
 * better source for it than the shipped INI, and `LiveStatus.ffx_fg_versions`
 * is that answer when there is one.
 */
export const FFX_FG_SECTION = "FSR";
export const FFX_FG_KEY = "FGIndex";
export const FFX_FG_ID = `${FFX_FG_SECTION}.${FFX_FG_KEY}`;

/**
 * Whether the FFX generator is the one in use. Nukem's and XeFG are other
 * implementations entirely and take no notice of this index; "auto" is included
 * because OptiScaler resolves it to FSR FG in the common case, and a running
 * game settles the question by reporting a version list or not.
 */
export function usesFfxFrameGen(values: ConfigValues): boolean {
  const output = get(values, "FrameGen", "FGOutput");
  return output === "fsrfg" || isAuto(output);
}

export function ffxFgChanges(index: string): OptionChange[] {
  return [change(FFX_FG_SECTION, FFX_FG_KEY, index)];
}

// -- The FFX upscaler version -----------------------------------------------

/**
 * Which version of FSR the FidelityFX backend runs.
 *
 * A different question from which backend runs, and the overlay asks both:
 * "Upscalers" picks fsr31 / xess / dlss, and the "FFX Upscaler" combo under
 * "FFX Settings" picks 4.1.1 / 3.1.5 / 2.3.4 within it. Only the FidelityFX
 * backend has versions to choose between — every other upscaler ignores the
 * index — and, as with the frame generator, the list belongs to the running
 * game rather than to the shipped INI: the FidelityFX SDK reports what it can
 * offer and OptiScaler stores the answer, which is what
 * `LiveStatus.ffx_upscaler_versions` carries.
 *
 * OptiScaler changes it with the same rebuild the upscaler switch uses, so it
 * applies without a restart wherever an upscaler switch would.
 */
export const FFX_UPSCALER_SECTION = "FSR";
export const FFX_UPSCALER_KEY = "UpscalerIndex";
export const FFX_UPSCALER_ID = `${FFX_UPSCALER_SECTION}.${FFX_UPSCALER_KEY}`;

/** The backend ids that run FidelityFX upscaling, and so have a version. */
export const FFX_BACKENDS = ["ffx", "ffx_12"];

export function isFfxBackend(code: string | null | undefined): boolean {
  return Boolean(code) && FFX_BACKENDS.includes(String(code).toLowerCase());
}

/**
 * Whether the FSR version is worth offering: the ini selects the FidelityFX
 * backend for some API, or "auto", which OptiScaler resolves to it on most of
 * the hardware this plugin runs on.
 */
export function usesFfxUpscaler(values: ConfigValues): boolean {
  const dx12 = get(values, "Upscalers", "Dx12Upscaler");
  return isFfxBackend(dx12) || isAuto(dx12);
}

/** Whether a FidelityFX version name — "4.1.1 *", "3.1.5" — is an FSR 4 one. */
export function isFsr4Version(name: string | null | undefined): boolean {
  const major = Number.parseInt(String(name ?? "").trim(), 10);
  return Number.isFinite(major) && major >= 4;
}

/**
 * Whether FSR 4 on this device only runs through the forced INT8 model.
 *
 * `experimental` is RDNA 2, which OptiScaler reaches through `Fsr4ForceEnableInt8`
 * rather than through its own GPU checks; `unsupported` is everything AMD does
 * not cover at all. Both are the devices the release notes warn about below.
 */
export function needsForcedInt8(gpu: GpuInfo | null | undefined): boolean {
  return gpu?.fsr4 === "experimental" || gpu?.fsr4 === "unsupported";
}

/**
 * Whether the FidelityFX upscaler in the folder is new enough for that override.
 *
 * This is not the same question as the GPU's, and it is the one that changes when
 * somebody swaps in a different build from the FSR 4 panel. OptiScaler's menu
 * offers its FSR 3.X/4 entry off `Fsr4ForceEnableInt8` only when the local
 * upscaler is 4.1.1 or newer (menu_common.cpp), so a 4.0.2 build — the one the
 * OptiScaler Client points RDNA 2 users at — is reached through `Fsr4Update`
 * instead, and the INT8 preset would do nothing at all with it in place.
 *
 * An unreadable version reads as yes: the file in an OptiScaler install is the
 * released 4.1.1 SDK unless somebody changed it, and the alternative is telling
 * every user of the bundled build to stop using the route that works for them.
 */
export function supportsInt8Override(ffx?: { version?: string | null } | null): boolean {
  const parts = String(ffx?.version ?? "").split(".");
  const major = Number.parseInt(parts[0] ?? "", 10);
  if (!Number.isFinite(major)) return true;
  const minor = Number.parseInt(parts[1] ?? "0", 10);
  return major > 4 || (major === 4 && (Number.isFinite(minor) ? minor : 0) >= 1);
}

/**
 * Pick a FidelityFX upscaler version, and make it reachable.
 *
 * Asking for FSR 4 is not enough on its own. OptiScaler only reaches it when
 * `fsr4Possible` holds — `Fsr4Update`, or an RDNA 4 GPU, or the INT8 override
 * (menu_common.cpp) — so asking for an FSR 4 version from the FSR 3.X backend
 * would otherwise fall back to FSR 3 with nothing said about it. That is the
 * "(Potential FSR3 fallback)" the overlay prints.
 *
 * `Fsr4Update` is only the right lever where OptiScaler's own GPU checks allow
 * it, which is RDNA 3 and up. Where the INT8 override is what reaches FSR 4, it
 * is the wrong one: v0.9.4's notes say setting it on an unsupported GPU forces
 * FP8 and OptiScaler answers with its internal FSR 3 fallback, and the
 * maintainer said the same thing on the bug tracker, pointing at the override as
 * the option such a device needs. So `int8Route` — the device and the upscaler
 * build together, as `BasicPanel` works it out — turns this write off, and the
 * caller says what to do instead.
 *
 * Note that the build is half of that condition: a 4.0.2 upscaler is below the
 * 4.1.1 the override needs, so on the same device the upgrade path is the one
 * that works and this write is the right answer again.
 *
 * The reverse is deliberately not done: choosing an older version does not turn
 * it off. `Fsr4Update` is the hook that makes FSR 4 *available*, not a request
 * for it, and switching it off would be undoing a setting nobody asked about.
 */
export function ffxUpscalerChanges(
  index: string, version?: string | null, int8Route = false
): OptionChange[] {
  // v10 removed Fsr4Update; the index alone decides which FSR the backend runs.
  // `version` and `int8Route` stay in the signature because callers work them
  // out together and the reasoning behind them still describes the choice.
  void version;
  void int8Route;
  return [change(FFX_UPSCALER_SECTION, FFX_UPSCALER_KEY, index)];
}

/**
 * The running game's two frame rates, when frame generation means there are two.
 *
 * `total` is what reaches the screen and `base` what the game renders. Both are
 * shown whenever frame generation is switched on, because "how much is frame
 * generation buying me" is the question it is turned on to answer and one
 * number can only ever be half of it.
 *
 * `base` is null when the rendered interval has not been read — an in-game
 * plugin older than this one does not report it, and a generator that was
 * created but has never presented leaves its slot at zero. The second tile
 * still appears, showing nothing: the pair is the feature, and a tile that
 * quietly fails to exist is indistinguishable from one that was never built.
 * `LivePanel` prints both intervals, which is where the difference is visible.
 *
 * `generating` is the separate question of whether the generator is actually
 * running. The setting being on does not mean it is: OptiScaler reports FSR-FG
 * as off until the game selects frame generation in its own options, and the
 * two rates then measure the same frames and come out equal. That is worth
 * saying rather than hiding — equal numbers with nothing to explain them read
 * as a broken readout.
 */
export function liveFrameRates(live: LiveStatus | null | undefined) {
  if (!live?.fg_enabled) return null;
  const number = (value: number | null | undefined) =>
    typeof value === "number" && value > 0 ? value : null;
  // The counter alone does not say which of the two rates it counted, so the
  // total comes from the derived pair when there is one and only falls back to
  // the raw count when there is not — where nothing has been generated and the
  // two are the same number anyway.
  const total = number(live.total_fps) ?? number(live.fps);
  const base = number(live.base_fps);
  if (total === null) return null;
  return { total, base, generating: base !== null && base < total * 0.95 };
}

/** The backend the running game ended up with, in the order it reports them. */
export function runningBackend(live: LiveStatus | null | undefined): string | null {
  return live?.upscaler?.dx12 ?? live?.upscaler?.vulkan ?? live?.upscaler?.dx11 ?? null;
}

/**
 * What to call the upscaler the running game ended up with.
 *
 * The backend id alone cannot be specific — "fsr31" is FSR 2.3.4 through 4.1.1
 * and OptiScaler names it "FSR 3.X/4" for exactly that reason. The version the
 * game actually built is in its own reported list, at the index Config holds,
 * and OptiScaler's overlay prints it the same way: "FSR " and the SDK's own
 * name. Falls back to the backend's name when there is no list to read, which
 * is every non-FidelityFX upscaler and any game that has not queried the SDK.
 */
export function liveUpscalerLabel(live: LiveStatus | null | undefined): string | null {
  const backend = runningBackend(live);
  if (!backend) return null;
  const versions = live?.ffx_upscaler_versions ?? [];
  const index = live?.ffx_upscaler_index;
  if (isFfxBackend(backend) && typeof index === "number" && versions[index]) {
    return `FSR ${versions[index]}`;
  }
  return UPSCALER_LABELS[backend] ?? backend;
}

/** The multiplier control only does anything on the XeSS FG output. */
export const MULTIPLIER_SECTION = "XeFG";
export const MULTIPLIER_KEY = "InterpolationCount";

export function frameGenEnabled(values: ConfigValues): boolean {
  return get(values, "FrameGen", "Enabled") === "true";
}

export function activeFgPreset(values: ConfigValues): Preset | undefined {
  return FG_PRESETS.find((preset) => preset.matches(values));
}

export function activeUpscalerPreset(values: ConfigValues): Preset | undefined {
  return UPSCALER_PRESETS.find((preset) => preset.matches(values));
}

export function supportsMultiplier(values: ConfigValues): boolean {
  return get(values, "FrameGen", "FGOutput") === "xefg";
}

/**
 * Turning frame generation on has to pick an input and an output too, or
 * OptiScaler comes up with FG "enabled" but doing nothing.
 */
export function enableFrameGenChanges(values: ConfigValues): OptionChange[] {
  const changes = [change("FrameGen", "Enabled", "true")];
  if (!activeFgPreset(values)) {
    changes.push(...FG_PRESETS[0].changes);
  }
  return changes;
}

export function disableFrameGenChanges(): OptionChange[] {
  return [change("FrameGen", "Enabled", "false")];
}

/**
 * Turn frame generation on with a named input and output pair.
 *
 * Automatic mode uses this instead of the preset list: the wiki names the pair
 * the game can actually feed, which is a stronger statement than any default
 * this plugin could pick, and it can be a combination no preset covers.
 */
export function enableFrameGenWith(input: string, output: string): OptionChange[] {
  return [
    change("FrameGen", "Enabled", "true"),
    change("FrameGen", "FGInput", input),
    change("FrameGen", "FGOutput", output),
  ];
}
