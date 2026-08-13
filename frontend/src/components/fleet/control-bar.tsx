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
    <section aria-label="Console controls" className="border-b border-[#e8e6e3] bg-white">
      <div className="mx-auto flex w-full max-w-[1120px] flex-col gap-4 px-4 py-4 md:flex-row md:items-end md:gap-6 md:px-6">
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 md:contents">
          <div className="flex min-w-0 flex-col gap-1.5">
            <label htmlFor="tenant" className="vf-label flex items-center gap-1.5">
              <Building2 className="size-3" aria-hidden />
              Tenant
            </label>
            <Select items={TENANTS} value={tenant} onValueChange={(value) => onTenantChange(String(value))}>
              <SelectTrigger
                id="tenant"
                size="default"
                className="h-10 w-full min-w-0 rounded-lg border-[#e8e6e3] bg-white text-[13px] md:h-8 md:w-[200px]"
              >
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

          <div className="flex min-w-0 flex-col gap-1.5">
            <label htmlFor="role" className="vf-label flex items-center gap-1.5">
              <ShieldCheck className="size-3" aria-hidden />
              Role
            </label>
            <Select items={ROLES} value={role} onValueChange={(value) => onRoleChange(String(value))}>
              <SelectTrigger
                id="role"
                size="default"
                className="h-10 w-full min-w-0 rounded-lg border-[#e8e6e3] bg-white text-[13px] md:h-8 md:w-[160px]"
              >
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
        </div>

        <label
          htmlFor="background-202"
          className="flex min-h-11 items-center gap-3 rounded-lg border border-[#e8e6e3] bg-[#fafaf8] px-3 py-2 md:ml-auto md:min-h-0 md:border-0 md:bg-transparent md:px-0 md:py-0"
        >
          <Switch
            id="background-202"
            size="default"
            checked={background202}
            onCheckedChange={onBackground202Change}
          />
          <span className="text-[13px] text-[#111]">
            Background 202
            <span className="ml-2 text-[#6f6e69]">
              {background202 ? "accept, then settle" : "wait inline"}
            </span>
          </span>
        </label>
      </div>
    </section>
  );
}
