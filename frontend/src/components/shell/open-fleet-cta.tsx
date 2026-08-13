"use client";

import Link from "next/link";
import { Button } from "@/components/ui/button";
import { useLocale } from "@/components/i18n/locale-provider";
import { cn } from "@/lib/utils";

export function OpenFleetCta({
  className,
  variant = "ink",
}: {
  className?: string;
  variant?: "ink" | "outline";
}) {
  const { t } = useLocale();
  const ink = variant === "ink";

  return (
    <Button
      render={<Link href="/fleet" />}
      nativeButton={false}
      variant="outline"
      className={cn(
        "h-10 rounded-lg px-4",
        ink
          ? "border-[#111] bg-[#111] text-white hover:bg-[#222] hover:text-white"
          : "border-[#e8e6e3] bg-white text-[#111] hover:bg-[#fafaf8]",
        className
      )}
    >
      {t("cta.fleet")}
    </Button>
  );
}
