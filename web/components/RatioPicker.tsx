"use client";
import { useEffect, useId, useRef, useState, type KeyboardEvent } from "react";
import { tr } from "../lib/i18n";
import { Icon } from "./ui";

const tall = ["1:1", "4:5", "3:4", "2:3", "9:16"];
const wide = ["5:4", "4:3", "3:2", "16:9", "21:9"];

function Frame({ ratio }: { ratio: string }) {
  const [w, h] = ratio.split(":").map(Number);
  const style = w >= h ? { width: "100%", height: (h / w) * 100 + "%" } : { width: (w / h) * 100 + "%", height: "100%" };
  return <span className="frame-box" aria-hidden="true"><span className="frame" style={style} /></span>;
}

export default function RatioPicker({ ratios, resolutions = [], storageKey, defaultValue = "4:5" }: { ratios: string[]; resolutions?: number[]; storageKey: string; defaultValue?: string }) {
  const available = [...tall, ...wide].filter(r => ratios.includes(r));
  const [value, setValue] = useState(() => {
    try {
      const saved = localStorage.getItem(storageKey);
      if (saved && available.includes(saved)) return saved;
    } catch {}
    return available.includes(defaultValue) ? defaultValue : available[0];
  });
  const [size, setSize] = useState(() => {
    const fallback = resolutions.includes(1920) ? 1920 : resolutions[0];
    try {
      const saved = Number(localStorage.getItem(storageKey + "-size"));
      return resolutions.includes(saved) ? saved : fallback;
    } catch {
      return fallback;
    }
  });
  const [open, setOpen] = useState(false);
  const root = useRef<HTMLDivElement>(null);
  const trigger = useRef<HTMLButtonElement>(null);
  const id = useId();

  useEffect(() => {
    if (!open) return;
    const outside = (event: MouseEvent) => { if (!root.current?.contains(event.target as Node)) setOpen(false); };
    document.addEventListener("mousedown", outside);
    root.current?.querySelector<HTMLElement>('[role="radio"][tabindex="0"]')?.focus();
    return () => document.removeEventListener("mousedown", outside);
  }, [open]);

  function choose(ratio: string) {
    setValue(ratio);
    try { localStorage.setItem(storageKey, ratio); } catch {}
    setOpen(false);
    trigger.current?.focus();
  }

  function chooseSize(next: number) {
    setSize(next);
    try { localStorage.setItem(storageKey + "-size", String(next)); } catch {}
  }

  function sizeKeys(event: KeyboardEvent<HTMLDivElement>) {
    const move: Record<string, number> = { ArrowDown: 1, ArrowRight: 1, ArrowUp: -1, ArrowLeft: -1 };
    if (!(event.key in move)) return;
    event.preventDefault();
    event.stopPropagation();
    const next = resolutions[(resolutions.indexOf(size) + move[event.key] + resolutions.length) % resolutions.length];
    chooseSize(next);
    requestAnimationFrame(() => event.currentTarget.querySelector<HTMLElement>('[role="radio"][tabindex="0"]')?.focus());
  }

  function keys(event: KeyboardEvent<HTMLDivElement>) {
    if (event.key === "Escape") { event.stopPropagation(); setOpen(false); trigger.current?.focus(); return; }
    const move: Record<string, number> = { ArrowDown: 1, ArrowRight: 1, ArrowUp: -1, ArrowLeft: -1 };
    if (!(event.key in move) && event.key !== "Home" && event.key !== "End") return;
    event.preventDefault();
    const order = [...tall, ...wide].filter(r => available.includes(r));
    const current = order.indexOf(value);
    const next = event.key === "Home" ? 0 : event.key === "End" ? order.length - 1 : (current + move[event.key] + order.length) % order.length;
    setValue(order[next]);
    requestAnimationFrame(() => root.current?.querySelector<HTMLElement>('[role="radio"][tabindex="0"]')?.focus());
  }

  if (!available.length) return null;
  const column = (list: string[]) => list.filter(r => available.includes(r)).map(r => (
    <button type="button" key={r} role="radio" aria-checked={value === r} tabIndex={value === r ? 0 : -1} className="ratio-option" onClick={() => choose(r)}>
      <Frame ratio={r} /><span>{r}</span>
    </button>
  ));

  return (
    <div className="ratio" ref={root}>
      <span className="field-label" id={id}>{tr("Formato")}</span>
      <input type="hidden" name="ratio" value={value} />
      {resolutions.length > 0 && <input type="hidden" name="resolution" value={size} />}
      <button type="button" ref={trigger} className="ratio-trigger" aria-haspopup="true" aria-expanded={open} aria-labelledby={id} onClick={() => setOpen(!open)}>
        <Frame ratio={value} /><span>{value}{resolutions.length > 0 && " · " + size + " px"}</span><Icon name="chevron-abajo" />
      </button>
      {open && (
        <div className="ratio-panel" role="radiogroup" aria-labelledby={id} onKeyDown={keys}>
          <div>{column(tall)}</div>
          <div>{column(wide)}</div>
          {resolutions.length > 0 && (
            <div className="size-group" role="radiogroup" aria-label={tr("Resolución")} onKeyDown={sizeKeys}>
              {resolutions.map(r => (
                <button type="button" key={r} role="radio" aria-checked={size === r} tabIndex={size === r ? 0 : -1} className="ratio-option" onClick={() => chooseSize(r)}>
                  {r} px
                </button>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
