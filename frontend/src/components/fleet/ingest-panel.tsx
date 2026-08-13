import { useRef, useState } from "react";
import { FileText, Layers, UploadCloud } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

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
    <section aria-label="Invoice ingest" className="grid grid-cols-1 gap-3 lg:grid-cols-[1fr_260px]">
      <div
        role="button"
        tabIndex={0}
        aria-label="Upload valid invoice PDF"
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
          "vf-panel-inset flex cursor-pointer items-center gap-3 rounded-sm px-4 py-4 outline-none transition-colors focus-visible:border-emerald-400/50",
          dragging || uploading ? "border-emerald-400/60 bg-emerald-400/[0.06]" : "hover:border-[#33456a]",
          uploading && "vf-busy"
        )}
      >
        <span className="flex size-9 shrink-0 items-center justify-center rounded-sm border border-[#26344f] bg-[#0b1220]">
          {fileName || uploading ? (
            <FileText className="size-4 text-emerald-300" />
          ) : (
            <UploadCloud className="size-4 text-slate-400" />
          )}
        </span>
        <span className="min-w-0">
          <span className="block text-[13px] font-medium tracking-tight text-slate-100">
            Valid invoice (PDF)
          </span>
          <span className="mt-0.5 block truncate font-mono text-[10px] uppercase tracking-[0.14em] text-slate-500">
            {uploading
              ? "queued · valid_invoice.pdf"
              : fileName
                ? `queued · ${fileName}`
                : "drop file or click to browse"}
          </span>
        </span>
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
        className="vf-glow h-auto w-full justify-center gap-2 rounded-sm border border-emerald-400/40 bg-emerald-400/10 py-4 font-mono text-[11px] uppercase tracking-[0.16em] text-emerald-200 hover:bg-emerald-400/20 disabled:opacity-60"
      >
        <Layers data-icon="inline-start" aria-hidden />
        {sweeping ? "Sweep running…" : "Run 3-invoice sweep"}
      </Button>
    </section>
  );
}
