import { useEffect, useState } from "react";

function truncateHash(hash: string) {
  if (hash.length <= 20) return hash;
  return `${hash.slice(0, 8)}…${hash.slice(-8)}`;
}

export function HashReveal({
  hash,
  animate = true,
}: {
  hash: string;
  animate?: boolean;
}) {
  const full = truncateHash(hash);
  const [count, setCount] = useState(animate ? 0 : full.length);

  useEffect(() => {
    if (!animate) {
      setCount(full.length);
      return;
    }
    const reduce =
      typeof window !== "undefined" &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reduce) {
      setCount(full.length);
      return;
    }
    setCount(0);
    let i = 0;
    const interval = window.setInterval(() => {
      i += 1;
      setCount(i);
      if (i >= full.length) window.clearInterval(interval);
    }, 26);
    return () => window.clearInterval(interval);
  }, [animate, full]);

  const done = count >= full.length;

  return (
    <span className="font-mono text-[#17663f]" aria-label={`hash ${full}`}>
      <span aria-hidden="true">{full.slice(0, count)}</span>
      {!done && (
        <span className="vf-caret ml-px inline-block text-[#18794e]" aria-hidden="true">
          ▌
        </span>
      )}
    </span>
  );
}
