import { ButtonItem, PanelSection, PanelSectionRow } from "@decky/ui";
import { toaster } from "@decky/api";
import { useState } from "react";
import { configureHeroic } from "../api";
import type { AutoPlan, GameDetail } from "../types";
import { Mono, Notice } from "./Common";

/** Heroic owns the Wine environment; its Steam shortcut must remain intact. */
export function HeroicSetup({ detail, plan, onChanged }: Readonly<{
  detail: GameDetail;
  plan?: AutoPlan | null;
  onChanged: () => Promise<void> | void;
}>) {
  const [busy, setBusy] = useState(false);
  const heroic = detail.heroic;
  if (!heroic) return null;
  const apply = async (restore: boolean) => {
    setBusy(true);
    try {
      const result = await configureHeroic(detail.path, detail.target, restore);
      toaster.toast({
        title: result.ok ? restore ? "Heroic settings restored" : "Heroic configured" : "Could not configure Heroic",
        body: result.ok ? "Launch the game normally through Heroic or its Steam shortcut." : String(result.error),
      });
      await onChanged();
    } catch (error) {
      toaster.toast({ title: "Could not configure Heroic", body: String(error) });
    } finally {
      setBusy(false);
    }
  };
  const needsOverride = Boolean(detail.install.filename?.toLowerCase().endsWith(".dll")) ||
    detail.reframework?.installed;
  return (
    <PanelSection title={heroic.flatpak ? "Heroic · Flatpak" : "Heroic"}>
      <PanelSectionRow>
        <Notice tone={heroic.error ? "warn" : "info"}>
          {heroic.error ?? (heroic.managed
            ? "Heroic's DLL overrides are configured. Removing OptiScaler restores the previous overrides. Quit the game and Heroic before changing these settings."
            : "After installing OptiScaler, enable its DLLs in Heroic here. Close the game and quit Heroic, including its tray icon, before changing these settings.")}
          {heroic.overrides ? <div>Current DLL overrides: <Mono>{heroic.overrides}</Mono></div> : null}
        </Notice>
      </PanelSectionRow>
      {plan?.launch_flags?.length ? (
        <PanelSectionRow>
          <Notice tone="warn" title="Additional launch settings">
            The compatibility entry also asks for <Mono>{plan.launch_flags.join(" ")}</Mono>.
            Add these in Heroic's per-game settings; the DLL action below does not set them.
          </Notice>
        </PanelSectionRow>
      ) : null}
      {detail.install.installed && needsOverride ? (
        <PanelSectionRow>
          <ButtonItem layout="below" disabled={busy || Boolean(heroic.error)} onClick={() => void apply(false)}>
            {busy ? "Working…" : heroic.managed ? "Update Heroic DLL overrides" : "Enable DLLs in Heroic"}
          </ButtonItem>
        </PanelSectionRow>
      ) : null}
      {heroic.managed ? (
        <PanelSectionRow>
          <ButtonItem layout="below" disabled={busy} onClick={() => void apply(true)}>
            Restore previous Heroic overrides
          </ButtonItem>
        </PanelSectionRow>
      ) : null}
    </PanelSection>
  );
}
