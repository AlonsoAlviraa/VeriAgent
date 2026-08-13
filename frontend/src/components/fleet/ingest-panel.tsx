"use client";

import { useRef, useState } from "react";
import { Layers, UploadCloud } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { useLocale } from "@/components/i18n/locale-provider";

export function IngestPanel({
  busy,
  activeJob,
  onUpload,
  onSweep,
}: {
  busy: boolean;
  activeJob: string;
  onUpload: () => void;
  onSweep: () => void;
}) {
  const { t } = useLocale();
  const [dragging, setDragging] = useState(false);
  const [fileName, setFileName] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const sweeping = busy && activeJob === "sweep";
  const uploading = busy && activeJob === "pdf";

  const dispatchPdf = (name?: string) => {
    setFileName(name ?? "valid_invoice.pdf");
    onUpload();
  };

  return (
    <section aria-label={t("ingest.aria")} className="grid grid-cols-1 gap-3 sm:grid-cols-[1fr_minmax(0,200px)]">
      <div
        role="button"
        tabIndex={0}
        aria-label={t("ingest.uploadAria")}
        onClick={() => inputRef.current?.click()}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            inputRef.current?.click();
          }
        }}
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragging(false);
          dispatchPdf("valid_invoice.pdf");
        }}
        className={cn(
          "flex min-h-[120px] cursor-pointer flex-col items-center justify-center gap-2 rounded-lg border border-dashed px-4 py-6 text-center outline-none transition-colors duration-150 focus-visible:border-[#18794e]",
          dragging || uploading
            ? "border-[#18794e] bg-[#eef8f1]"
            : "border-[#e8e6e3] bg-[#f4f3f0] hover:border-[#cfcbc4]"
        )}
      >
        <UploadCloud className="size-5 text-[#6f6e69]" />
        <span className="text-[14px] font-medium text-[#111]">
          {uploading ? t("ingest.uploading") : fileName || t("ingest.drop")}
        </span>
        <span className="text-[12px] text-[#6f6e69]">{t("ingest.browse")}</span>
        <input
          ref={inputRef}
          type="file"
          accept="application/pdf"
          className="hidden"
          onChange={(e) => {
            dispatchPdf("valid_invoice.pdf");
            e.target.value = "";
          }}
        />
      </div>

      <Button
        onClick={onSweep}
        disabled={busy}
        className="h-auto min-h-[120px] w-full justify-center gap-2 rounded-lg bg-[#111] py-4 text-[12px] font-medium tracking-[0.12em] text-white uppercase transition-colors duration-150 hover:bg-emerald-400 hover:text-[#04180f] disabled:opacity-50"
      >
        <Layers data-icon="inline-start" aria-hidden />
        {sweeping ? t("ingest.sweeping") : t("ingest.sweep")}
      </Button>
    </section>
  );
}
