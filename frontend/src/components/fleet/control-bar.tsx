"use client";

import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { useLocale } from "@/components/i18n/locale-provider";
import { AeatStatusChip } from "./aeat-status-chip";

const TENANTS = [
  { label: "enterprise-demo", value: "enterprise-demo" },
  { label: "default", value: "default" },
];

const ROLES = [
  { label: "issuer", value: "issuer" },
  { label: "auditor", value: "auditor" },
  { label: "admin", value: "admin" },
];

const chipSelect =
  "h-auto min-h-0 w-auto min-w-0 border-0 bg-transparent p-0 text-[12px] text-[#111] shadow-none ring-0 focus-visible:ring-0 data-[size=default]:h-auto";

export function ControlBar({
  tenant,
  onTenantChange,
  role,
  onRoleChange,
  background202,
  onBackground202Change,
  userId,
  onOpenShortcuts,
}: {
  tenant: string;
  onTenantChange: (tenant: string) => void;
  role: string;
  onRoleChange: (role: string) => void;
  background202: boolean;
  onBackground202Change: (value: boolean) => void;
  userId?: string;
  onOpenShortcuts?: () => void;
}) {
  const { t } = useLocale();

  return (
    <section aria-label={t("control.aria")} className="vf-no-print border-b border-[#e8e6e3]">
      <div className="mx-auto flex w-full max-w-[1120px] flex-wrap items-center gap-2 px-4 py-3 md:px-6">
        <div className="vf-chip min-h-11 min-w-0 md:min-h-8">
          <span>{t("control.tenant")}</span>
          <Select items={TENANTS} value={tenant} onValueChange={(value) => onTenantChange(String(value))}>
            <SelectTrigger id="tenant" size="default" className={chipSelect}>
              <SelectValue />
            </SelectTrigger>
            <SelectContent className="border-[#e8e6e3] bg-white text-[13px]">
              <SelectGroup>
                {TENANTS.map((item) => (
                  <SelectItem key={item.value} value={item.value}>
                    {item.label}
                  </SelectItem>
                ))}
              </SelectGroup>
            </SelectContent>
          </Select>
        </div>

        <div className="vf-chip min-h-11 min-w-0 md:min-h-8">
          <span>{t("control.role")}</span>
          <Select items={ROLES} value={role} onValueChange={(value) => onRoleChange(String(value))}>
            <SelectTrigger id="role" size="default" className={chipSelect}>
              <SelectValue />
            </SelectTrigger>
            <SelectContent className="border-[#e8e6e3] bg-white text-[13px]">
              <SelectGroup>
                {ROLES.map((item) => (
                  <SelectItem key={item.value} value={item.value}>
                    {item.label}
                  </SelectItem>
                ))}
              </SelectGroup>
            </SelectContent>
          </Select>
        </div>

        <span className="vf-chip min-h-11 md:min-h-8">
          {userId || "judge"}
        </span>

        <AeatStatusChip />

        <label
          htmlFor="background-202"
          className="vf-chip min-h-11 cursor-pointer gap-2 md:ml-auto md:min-h-8"
        >
          <Switch
            id="background-202"
            size="sm"
            checked={background202}
            onCheckedChange={onBackground202Change}
          />
          <span className="text-[#111]">
            {t("control.background202")}
            <span className="ml-1 text-[#6f6e69]">
              {background202 ? t("control.accept") : t("control.inline")}
            </span>
          </span>
        </label>

        {onOpenShortcuts ? (
          <button
            type="button"
            onClick={onOpenShortcuts}
            aria-label={t("shortcuts.aria")}
            className="vf-chip min-h-11 cursor-pointer md:min-h-8"
          >
            <kbd className="font-mono text-[12px] text-[#111]">?</kbd>
            <span className="text-[#111]">{t("shortcuts.open")}</span>
          </button>
        ) : null}
      </div>
    </section>
  );
}
