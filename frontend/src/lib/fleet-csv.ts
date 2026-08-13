/** Client-side CSV from already-fetched fleet runs. Never invents a hash. */

export type CsvRun = {
  run_id: string;
  decision?: string | null;
  invoice_hash?: string | null;
  reason?: string | null;
};

export function truncateHash(hash?: string | null): string {
  if (!hash) return "";
  if (hash.length <= 16) return hash;
  return `${hash.slice(0, 8)}…${hash.slice(-8)}`;
}

function csvCell(value: string): string {
  if (/[",\n\r]/.test(value)) return `"${value.replaceAll('"', '""')}"`;
  return value;
}

export function runsToCsv(runs: CsvRun[]): string {
  const header = ["run_id", "verdict", "hash", "reason"];
  const lines = [header.join(",")];
  for (const run of runs) {
    lines.push(
      [
        csvCell(run.run_id ?? ""),
        csvCell(run.decision ?? ""),
        csvCell(truncateHash(run.invoice_hash)),
        csvCell(run.reason ?? ""),
      ].join(",")
    );
  }
  return `${lines.join("\n")}\n`;
}

export function downloadTextFile(filename: string, text: string, mime = "text/csv;charset=utf-8") {
  const blob = new Blob([text], { type: mime });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.rel = "noopener";
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}
