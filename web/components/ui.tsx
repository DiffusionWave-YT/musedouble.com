import Link from "next/link";
import { useEffect, useRef, useState, type KeyboardEvent, type ReactNode } from "react";
import { setLang, tr, useLang } from "../lib/i18n";

const own = ["cuadricula", "lista", "ordenar"];

export function Icon({ name }: { name: string }) {
  const file = own.includes(name) ? "propios" : "sprite";
  return <svg className="icon" aria-hidden="true" focusable="false"><use href={"/iconos/" + file + ".svg#i-" + name} /></svg>;
}

export function Brand() {
  return <span className="brand"><b aria-hidden="true">m</b><span className="label">MuseDouble</span></span>;
}

export function BrandHome() {
  return <Link href="/home" className="brand-home" aria-label={"MuseDouble, " + tr("inicio")}><Brand /></Link>;
}

export function Empty({ title, text, icon = "imagen" }: { title: string; text: string; icon?: string }) {
  return <div className="empty"><span className="ic-ficha ic-tono-morado" aria-hidden="true"><Icon name={icon} /></span><h2>{title}</h2><p>{text}</p></div>;
}

const languages = [["es", "Español"], ["en", "English"]] as const;

export function LangToggle() {
  const lang = useLang();
  const [open, setOpen] = useState(false);
  const root = useRef<HTMLDivElement>(null);
  const trigger = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!open) return;
    const outside = (event: MouseEvent) => { if (!root.current?.contains(event.target as Node)) setOpen(false); };
    document.addEventListener("mousedown", outside);
    root.current?.querySelector<HTMLElement>('[aria-checked="true"]')?.focus();
    return () => document.removeEventListener("mousedown", outside);
  }, [open]);

  function choose(code: "es" | "en") {
    setLang(code);
    setOpen(false);
    trigger.current?.focus();
  }

  function keys(event: KeyboardEvent<HTMLDivElement>) {
    if (event.key === "Escape") { event.stopPropagation(); setOpen(false); trigger.current?.focus(); return; }
    if (event.key !== "ArrowDown" && event.key !== "ArrowUp") return;
    event.preventDefault();
    const entries = Array.from(event.currentTarget.querySelectorAll<HTMLElement>('[role="menuitemradio"]'));
    const index = entries.indexOf(document.activeElement as HTMLElement);
    entries[(index + (event.key === "ArrowDown" ? 1 : -1) + entries.length) % entries.length]?.focus();
  }

  return (
    <div className="menu-wrap lang-menu" ref={root}>
      <button type="button" ref={trigger} className="quiet" aria-haspopup="menu" aria-expanded={open} aria-label={tr("Idioma") + ": " + languages.find(l => l[0] === lang)![1]} onClick={() => setOpen(!open)}>
        <span className="lang-code">{lang.toUpperCase()}</span><Icon name="chevron-abajo" />
      </button>
      {open && (
        <div className="menu" role="menu" aria-label={tr("Idioma")} onKeyDown={keys}>
          {languages.map(([code, label]) => (
            <button type="button" key={code} lang={code} role="menuitemradio" aria-checked={lang === code} onClick={() => choose(code)}>
              <span>{label}</span>{lang === code && <Icon name="check" />}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

export function Action({ icon, children }: { icon: string; children: ReactNode }) {
  return <><Icon name={icon} /><span className="label">{children}</span></>;
}
