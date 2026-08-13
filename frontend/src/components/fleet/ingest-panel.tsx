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
    <section aria-label="Invoice ingest" className="grid grid-cols-1 gap-3 sm:grid-cols-[1fr_minmax(0,220px)]">
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
          "flex min-h-[88px] cursor-pointer items-center gap-3 rounded-lg border border-dashed px-4 py-4 outline-none transition-colors duration-150 focus-visible:border-[#18794e]",
          dragging || uploading
            ? "border-[#18794e] bg-[#eef8f1]"
            : "border-[#e8e6e3] bg-white hover:border-[#cfcbc4]"
        )}
      >
        <span className="flex size-10 shrink-0 items-center justify-center rounded-md border border-[#e8e6e3] bg-[#fafaf8]">
          {fileName || uploading ? (
            <FileText className="size-4 text-[#18794e]" />
          ) : (
            <UploadCloud className="size-4 text-[#6f6e69]" />
          )}
        </span>
        <span className="min-w-0">
          <span className="block text-[14px] font-medium text-[#111]">
            Valid invoice PDF
          </span>
          <span className="mt-0.5 block truncate text-[12px] text-[#6f6e69]">
            {uploading
              ? "Uploading valid_invoice.pdf…"
              : fileName
                ? fileName
                : "Drop a file or click to browse"}
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
        className="h-auto min-h-[88px] w-full justify-center gap-2 rounded-lg bg-[#111] py-4 text-[13px] font-medium text-white transition-colors duration-150 hover:bg-[#18794e] disabled:opacity-50"
      >
        <Layers data-icon="inline-start" aria-hidden />
        {sweeping ? "Sweep running…" : "Run 3-invoice sweep"}
      </Button>
    </section>
  );
}
