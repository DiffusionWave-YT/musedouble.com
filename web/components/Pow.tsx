"use client";
import { useEffect, useRef, useState } from "react";
import { api } from "../lib/api";
import { tr } from "../lib/i18n";

const BATCH = 256;

function zeroBits(bytes: Uint8Array) {
  let count = 0;
  for (const byte of bytes) {
    if (byte === 0) { count += 8; continue; }
    return count + Math.clz32(byte) - 24;
  }
  return count;
}

async function solve(challenge: string, bits: number, stop: () => boolean) {
  const encoder = new TextEncoder();
  for (let start = 0; ; start += BATCH) {
    if (stop()) return null;
    const names = Array.from({ length: BATCH }, (_, i) => (start + i).toString(36));
    const hashes = await Promise.all(names.map(name => crypto.subtle.digest("SHA-256", encoder.encode(challenge + ":" + name))));
    for (let i = 0; i < BATCH; i++) {
      if (zeroBits(new Uint8Array(hashes[i])) >= bits) return names[i];
    }
  }
}

export function Pow({ onToken, resetKey }: { onToken: (token: string) => void; resetKey: number }) {
  const [state, setState] = useState<"working" | "ready" | "failed">("working");
  const callback = useRef(onToken);
  callback.current = onToken;

  useEffect(() => {
    let gone = false;
    setState("working");
    callback.current("");
    (async () => {
      try {
        const given = await api<{ challenge: string; bits: number }>("/auth/challenge");
        const nonce = await solve(given.challenge, given.bits, () => gone);
        if (gone || nonce === null) return;
        callback.current(given.challenge + "|" + nonce);
        setState("ready");
      } catch {
        if (!gone) setState("failed");
      }
    })();
    return () => { gone = true; };
  }, [resetKey]);

  return (
    <p className="pow" role="status" aria-live="polite">
      {state === "working" ? tr("Comprobando que eres una persona…") : state === "ready" ? tr("Verificación lista.") : tr("No se pudo completar la verificación. Recarga la página.")}
    </p>
  );
}
