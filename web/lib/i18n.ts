import { useSyncExternalStore } from "react";
import { en } from "./en";

export type Lang = "es" | "en";

const key = "muse-lang";
const listeners = new Set<() => void>();
let lang: Lang = "es";
let started = false;

function start() {
  if (started || typeof window === "undefined") return;
  started = true;
  try {
    const saved = localStorage.getItem(key);
    lang = saved === "en" || saved === "es" ? saved : navigator.language.toLowerCase().startsWith("es") ? "es" : "en";
  } catch {}
  document.documentElement.lang = lang;
  listeners.forEach(listener => listener());
}

export function setLang(next: Lang) {
  start();
  lang = next;
  try { localStorage.setItem(key, next); } catch {}
  document.documentElement.lang = next;
  listeners.forEach(listener => listener());
}

const snapshot = (): Lang => lang;

export function useLang(): Lang {
  return useSyncExternalStore(
    listener => { listeners.add(listener); start(); return () => { listeners.delete(listener); }; },
    snapshot,
    () => "es",
  );
}

export function tr(text: string, vars?: Record<string, string | number>): string {
  let out = lang === "en" ? en[text] ?? text : text;
  if (vars) for (const name of Object.keys(vars)) out = out.split("{" + name + "}").join(String(vars[name]));
  return out;
}

export const locale = () => (lang === "en" ? "en" : "es");
