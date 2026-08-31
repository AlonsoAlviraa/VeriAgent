"use client";

import { cn } from "@/lib/utils";
import { useLocale } from "./locale-provider";
import type { Locale } from "@/lib/i18n";

const OPTIONS: Locale[] = ["es", "en"];

export function LocaleToggle({ className }: { className?: string }) {
  const { locale, setLocale, t } = useLocale();

  return (
    <div
      role="group"
      aria-label={t("nav.lang")}
      className={cn("inline-flex shrink-0 items-center gap-1 text-[12px] font-medium", className)}
    >
      {OPTIONS.map((option, index) => (
        <span key={option} className="inline-flex items-center gap-1">
          {index > 0 ? <span className="text-[#cfcbc4]">|</span> : null}
          <button
            type="button"
            aria-pressed={locale === option}
            onClick={() => setLocale(option)}
            className={cn(
              "min-h-8 min-w-8 rounded-md px-1.5 uppercase tracking-[0.08em] transition-colors duration-150",
              locale === option ? "font-semibold text-[#111]" : "text-[#6f6e69] hover:text-[#111]"
            )}
          >
            {option}
          </button>
        </span>
      ))}
    </div>
  );
}
