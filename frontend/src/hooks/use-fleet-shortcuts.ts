"use client";

import { useEffect, useState } from "react";
import { FIXTURES } from "@/components/fleet/fixture-grid";

export const FLEET_DROPZONE_ID = "fleet-dropzone";

function isTypingTarget(target: EventTarget | null) {
  if (!(target instanceof HTMLElement)) return false;
  const tag = target.tagName;
  if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return true;
  if (target.isContentEditable) return true;
  return Boolean(target.closest('[role="listbox"], [role="menu"], [role="combobox"]'));
}

export function useFleetShortcuts({
  busy,
  onDispatch,
  onToggleBackground,
}: {
  busy: boolean;
  onDispatch: (path: string) => void;
  onToggleBackground: () => void;
}) {
  const [cheatsheetOpen, setCheatsheetOpen] = useState(false);

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.defaultPrevented) return;
      if (event.metaKey || event.ctrlKey || event.altKey) return;

      const helpKey = event.key === "?" || event.key === "¿";

      if (cheatsheetOpen) {
        if (event.key === "Escape" || helpKey) {
          event.preventDefault();
          setCheatsheetOpen(false);
        }
        return;
      }

      if (isTypingTarget(event.target)) return;

      if (helpKey) {
        event.preventDefault();
        setCheatsheetOpen(true);
        return;
      }

      if (event.key === "g" || event.key === "G") {
        event.preventDefault();
        onToggleBackground();
        return;
      }

      if (event.key === "u" || event.key === "U") {
        event.preventDefault();
        document.getElementById(FLEET_DROPZONE_ID)?.focus();
        return;
      }

      const index = Number(event.key) - 1;
      if (event.key >= "1" && event.key <= "4" && !busy) {
        const fixture = FIXTURES[index];
        if (!fixture) return;
        event.preventDefault();
        onDispatch(fixture.path);
      }
    };

    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [busy, cheatsheetOpen, onDispatch, onToggleBackground]);

  return { cheatsheetOpen, setCheatsheetOpen };
}
