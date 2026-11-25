"use client";
import Link from "next/link";
import { flushSync } from "react-dom";
import { useEffect, useLayoutEffect, useRef, useState, type KeyboardEvent, type ReactNode } from "react";
import { tr } from "../lib/i18n";
import { Brand, Icon } from "./ui";
import type { Group, Section } from "../lib/sections";
import type { User } from "../lib/api";

type Props = {
  groups: Group[];
  account: Section;
  currentId: string;
  title: string;
  user: User;
  credits: number | null;
  active: { count: number; percent: number };
  actions: ReactNode;
  children: ReactNode;
};

type Tip = { text: string; top: number; left: number };

const EASE = "cubic-bezier(.4,0,.2,1)";
const reduced = () => window.matchMedia("(prefers-reduced-motion: reduce)").matches;

function useMedia(query: string) {
  const [matches, setMatches] = useState(false);
  useEffect(() => {
    const list = window.matchMedia(query);
    const update = () => setMatches(list.matches);
    update();
    list.addEventListener("change", update);
    return () => list.removeEventListener("change", update);
  }, [query]);
  return matches;
}

export default function Shell({ groups, account, currentId, title, user, credits, active, actions, children }: Props) {
  const mobile = useMedia("(max-width: 47.99rem)");
  const narrow = useMedia("(max-width: 63.99rem)");
  const [collapsed, setCollapsed] = useState(() => {
    try { return localStorage.getItem("muse-sidebar") === "collapsed"; } catch { return false; }
  });
  const [open, setOpen] = useState(false);
  const [tip, setTip] = useState<Tip | null>(null);
  const asideRef = useRef<HTMLElement>(null);
  const navRef = useRef<HTMLElement>(null);
  const barRef = useRef<HTMLSpanElement>(null);
  const menuRef = useRef<HTMLButtonElement>(null);
  const toggleRef = useRef<HTMLButtonElement>(null);
  const widthMotion = useRef<Animation | null>(null);
  const previousBar = useRef<{ top: number; height: number } | null>(null);
  const tipTimer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const iconOnly = !mobile && (collapsed || narrow);

  function collapse() {
    const element = asideRef.current;
    if (!element) return;
    const from = element.getBoundingClientRect().width;
    const next = !collapsed;
    flushSync(() => setCollapsed(next));
    try { localStorage.setItem("muse-sidebar", next ? "collapsed" : "expanded"); } catch {}
    const to = element.getBoundingClientRect().width;
    widthMotion.current?.cancel();
    widthMotion.current = element.animate([{ width: from + "px" }, { width: to + "px" }], { duration: reduced() ? 300 : 520, easing: EASE });
  }

  function openDrawer() {
    flushSync(() => setOpen(true));
    const duration = reduced() ? 260 : 420;
    asideRef.current?.animate([{ transform: "translateX(-100%)" }, { transform: "translateX(0)" }], { duration, easing: EASE });
    document.querySelector(".scrim")?.animate([{ opacity: 0 }, { opacity: 1 }], { duration });
    toggleRef.current?.focus();
  }

  function closeDrawer(restoreFocus = true) {
    if (!open) return;
    const duration = reduced() ? 260 : 420;
    const slide = asideRef.current?.animate([{ transform: "translateX(0)" }, { transform: "translateX(-100%)" }], { duration, easing: EASE, fill: "forwards" });
    document.querySelector(".scrim")?.animate([{ opacity: 1 }, { opacity: 0 }], { duration, fill: "forwards" });
    const finish = () => {
      flushSync(() => setOpen(false));
      slide?.cancel();
      if (restoreFocus) menuRef.current?.focus();
    };
    if (slide) slide.finished.then(finish, finish); else finish();
  }

  useEffect(() => {
    function keys(event: globalThis.KeyboardEvent) {
      const target = event.target as HTMLElement;
      if (/^(INPUT|TEXTAREA|SELECT)$/.test(target.tagName) || target.isContentEditable) return;
      if (event.key === "[") { event.preventDefault(); if (mobile) { if (open) closeDrawer(); else openDrawer(); } else collapse(); }
      if (event.key === "Escape" && mobile && open) closeDrawer();
    }
    let startX = 0;
    let startY = 0;
    const touchStart = (event: TouchEvent) => { startX = event.touches[0].clientX; startY = event.touches[0].clientY; };
    const touchEnd = (event: TouchEvent) => {
      const dx = event.changedTouches[0].clientX - startX;
      const dy = Math.abs(event.changedTouches[0].clientY - startY);
      if (!mobile || dy > 40) return;
      if (!open && startX < 32 && dx > 60) openDrawer();
      if (open && dx < -60) closeDrawer();
    };
    document.addEventListener("keydown", keys);
    document.addEventListener("touchstart", touchStart, { passive: true });
    document.addEventListener("touchend", touchEnd, { passive: true });
    return () => {
      document.removeEventListener("keydown", keys);
      document.removeEventListener("touchstart", touchStart);
      document.removeEventListener("touchend", touchEnd);
    };
  });

  useEffect(() => { if (!mobile && open) setOpen(false); }, [mobile, open]);

  useLayoutEffect(() => {
    const nav = navRef.current;
    const bar = barRef.current;
    if (!nav || !bar) return;
    const link = nav.querySelector<HTMLElement>('[aria-current="page"]');
    if (!link) { bar.style.opacity = "0"; previousBar.current = null; return; }
    const next = { top: link.offsetTop, height: link.offsetHeight };
    bar.style.opacity = "1";
    bar.style.height = next.height + "px";
    bar.style.transform = "translateY(" + next.top + "px)";
    const before = previousBar.current;
    if (before && before.top !== next.top) {
      bar.animate([{ transform: "translateY(" + before.top + "px)", height: before.height + "px" }, { transform: "translateY(" + next.top + "px)", height: next.height + "px" }], { duration: reduced() ? 160 : 250, easing: EASE });
    }
    previousBar.current = next;
  }, [currentId, iconOnly, open, groups]);

  function showTip(text: string, element: HTMLElement) {
    if (!iconOnly) return;
    clearTimeout(tipTimer.current);
    tipTimer.current = setTimeout(() => {
      const box = element.getBoundingClientRect();
      setTip({ text, top: box.top + box.height / 2, left: box.right + 10 });
    }, 250);
  }

  function hideTip() { clearTimeout(tipTimer.current); setTip(null); }

  function arrows(event: KeyboardEvent<HTMLElement>) {
    const keys = ["ArrowDown", "ArrowUp", "Home", "End"];
    if (!keys.includes(event.key)) return;
    const links = Array.from(event.currentTarget.querySelectorAll<HTMLElement>("a"));
    const index = links.indexOf(document.activeElement as HTMLElement);
    const target = event.key === "Home" ? 0 : event.key === "End" ? links.length - 1 : event.key === "ArrowDown" ? Math.min(index + 1, links.length - 1) : Math.max(index - 1, 0);
    event.preventDefault();
    links[target]?.focus();
  }

  const select = () => { if (mobile && open) setTimeout(() => closeDrawer(), 260); };
  const accountCurrent = currentId === account.id;
  const link = (item: Section) => (
    <Link key={item.id} href={item.path} aria-current={currentId === item.id ? "page" : undefined} onClick={select}
      onMouseEnter={e => showTip(tr(item.name), e.currentTarget)} onMouseLeave={hideTip}
      onFocus={e => showTip(tr(item.name), e.currentTarget)} onBlur={hideTip}>
      <span className={"ic-ficha ic-tono-" + item.tone} aria-hidden="true"><Icon name={item.icon} /></span>
      <span className="label">{tr(item.name)}</span>
    </Link>
  );

  return (
    <div className={"shell" + (iconOnly ? " is-collapsed" : "") + (open ? " is-open" : "")}>
      <aside id="sidebar" ref={asideRef} inert={mobile && !open ? true : undefined}>
        <button ref={toggleRef} className="icon-btn side-toggle" onClick={() => (mobile ? closeDrawer() : collapse())}
          aria-label={mobile ? tr("Cerrar navegación") : iconOnly ? tr("Expandir barra lateral") : tr("Contraer barra lateral")}
          aria-expanded={mobile ? open : !iconOnly}>
          <Icon name={mobile ? "cerrar" : iconOnly ? "barra-expandir" : "barra-contraer"} />
        </button>
        <Link href="/home" className="brand-link" aria-label={"MuseDouble, " + tr("inicio")} onClick={select}><Brand /></Link>
        <nav ref={navRef} aria-label={tr("Navegación principal")} onKeyDown={arrows}>
          <span ref={barRef} className="indicator" aria-hidden="true" />
          {groups.map((group, index) => (
            <div className="group" key={index}>
              {group.label && <p className="group-label"><span className="label">{tr(group.label)}</span></p>}
              {group.items.map(link)}
            </div>
          ))}
        </nav>
        <div className="side-foot">
          {active.count > 0 && (
            <div className="live" role="status">
              <svg viewBox="0 0 36 36" className="ring" aria-hidden="true">
                <circle cx="18" cy="18" r="15.9" pathLength="100" className="ring-track" />
                <circle cx="18" cy="18" r="15.9" pathLength="100" className="ring-value" strokeDasharray={active.percent + " 100"} />
              </svg>
              <span className="label"><strong>{active.percent}%</strong><small>{active.count === 1 ? tr("1 en curso") : tr("{n} en curso", { n: active.count })}</small></span>
            </div>
          )}
          <Link href={account.path} className="account" aria-current={accountCurrent ? "page" : undefined} onClick={select}
            onMouseEnter={e => showTip(tr(account.name), e.currentTarget)} onMouseLeave={hideTip}
            onFocus={e => showTip(tr(account.name), e.currentTarget)} onBlur={hideTip}>
            <span className="avatar" aria-hidden="true">{user.name.slice(0, 1)}</span>
            <span className="label"><strong>{user.name}</strong><small>{credits === null ? "—" : credits} {tr("créditos")}</small></span>
          </Link>
        </div>
      </aside>
      {open && <div className="scrim" onClick={() => closeDrawer()} aria-hidden="true" />}
      <div className="body" inert={open ? true : undefined}>
        <header>
          <button ref={menuRef} className="icon-btn menu-btn" aria-label={tr("Abrir navegación")} aria-expanded={open} aria-controls="sidebar" onClick={openDrawer}>
            <Icon name="menu" />
          </button>
          <h1>{title}</h1>
          <div className="header-actions">{actions}</div>
        </header>
        <main className="content">{children}</main>
      </div>
      {tip && <div className="tip" role="tooltip" style={{ top: tip.top, left: tip.left }}>{tip.text}</div>}
    </div>
  );
}
