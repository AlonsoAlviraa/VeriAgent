export function ReplayHint() {
  return (
    <p className="text-[12px] leading-relaxed text-[#6f6e69]">
      Judge replay:{" "}
      <code className="font-mono text-[11px] text-[#111]">pytest tests/test_fleet_adk.py</code>
      {" · "}
      fixtures in <code className="font-mono text-[11px] text-[#111]">/demo-fixtures</code>
    </p>
  );
}
