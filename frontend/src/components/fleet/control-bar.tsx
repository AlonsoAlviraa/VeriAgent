import { Building2, ShieldCheck } from "lucide-react";
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";

const TENANTS = [
  { label: "enterprise-demo", value: "enterprise-demo" },
  { label: "default", value: "default" },
];

const ROLES = [
  { label: "issuer", value: "issuer" },
  { label: "auditor", value: "auditor" },
  { label: "admin", value: "admin" },
];

export function ControlBar({
  tenant,
  onTenantChange,
  role,
  onRoleChange,
  background202,
  onBackground202Change,
}: {
  tenant: string;
  onTenantChange: (tenant: string) => void;
  role: string;
  onRoleChange: (role: string) => void;
  background202: boolean;
  onBackground202Change: (value: boolean) => void;
}) {
  return (
    <section aria-label="Console controls" className="border-b border-[#1e2b45] bg-[#0d1524]/70">
      <div className="mx-auto flex w-full max-w-[1280px] flex-col gap-3 px-4 py-3 md:flex-row md:items-center md:gap-6 md:px-6">
        <div className="flex min-w-0 flex-col gap-1.5 sm:flex-row sm:items-center sm:gap-3">
          <label
            htmlFor="tenant"
            className="flex items-center gap-1.5 font-mono text-[10px] uppercase tracking-[0.16em] text-slate-500"
          >
            <Building2 className="size-3" aria-hidden />
            Tenant
          </label>
          <Select items={TENANTS} value={tenant} onValueChange={(value) => onTenantChange(String(value))}>
            <SelectTrigger
              id="tenant"
              size="sm"
              className="w-full min-w-0 rounded-sm border-[#243350] bg-[#0b1220] font-mono text-[11px] text-slate-200 sm:w-[190px]"
            >
              <SelectValue />
            </SelectTrigger>
            <SelectContent className="border-[#243350] bg-[#0d1524] font-mono text-[11px]">
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

        <div className="hidden h-6 w-px bg-[#1e2b45] md:block" aria-hidden />

        <div className="flex min-w-0 flex-col gap-1.5 sm:flex-row sm:items-center sm:gap-3">
          <label
            htmlFor="role"
            className="flex items-center gap-1.5 font-mono text-[10px] uppercase tracking-[0.16em] text-slate-500"
          >
            <ShieldCheck className="size-3" aria-hidden />
            Role
          </label>
          <Select items={ROLES} value={role} onValueChange={(value) => onRoleChange(String(value))}>
            <SelectTrigger
              id="role"
              size="sm"
              className="w-full min-w-0 rounded-sm border-[#243350] bg-[#0b1220] font-mono text-[11px] text-slate-200 sm:w-[150px]"
            >
              <SelectValue />
            </SelectTrigger>
            <SelectContent className="border-[#243350] bg-[#0d1524] font-mono text-[11px]">
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

        <div className="flex items-center gap-3 md:ml-auto">
          <Switch
            id="background-202"
            size="sm"
            checked={background202}
            onCheckedChange={onBackground202Change}
          />
          <label
            htmlFor="background-202"
            className="font-mono text-[10px] uppercase tracking-[0.16em] text-slate-400"
          >
            Background 202
            <span className="ml-2 text-slate-600">
              {background202 ? "accept → settle" : "inline"}
            </span>
          </label>
        </div>
      </div>
    </section>
  );
}
