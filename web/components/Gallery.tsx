"use client";
import { useCallback, useEffect, useRef, useState, type KeyboardEvent } from "react";
import { api, type Gallery as GalleryData, type GalleryItem } from "../lib/api";
import { useSignedImage } from "./Results";
import { Action, Empty, Icon } from "./ui";

const orders = [["newest", "Más nuevas"], ["oldest", "Más antiguas"], ["az", "A–Z"], ["za", "Z–A"]] as const;
type Order = (typeof orders)[number][0];
type View = "grid" | "list";

function remembered<T extends string>(key: string, allowed: readonly T[], fallback: T): T {
  try {
    const value = localStorage.getItem(key);
    return allowed.includes(value as T) ? (value as T) : fallback;
  } catch {
    return fallback;
  }
}

const age = (value: string) => new Date(value).toLocaleDateString("es", { day: "numeric", month: "short", year: "numeric" });

function Tile({ item }: { item: GalleryItem }) {
  const { url, error, failed } = useSignedImage(item.id);
  const label = item.name + (item.ratio ? ", " + item.ratio : "");
  return (
    <a className="tile" href={url || undefined} target="_blank" rel="noreferrer" aria-label={label}>
      {url ? <img src={url} alt="" loading="lazy" onError={failed} /> : <span className="tile-state">{error ? "Sin vista previa" : ""}</span>}
      <span className="tile-name">{item.name}</span>
    </a>
  );
}

function Row({ item }: { item: GalleryItem }) {
  const { url, error, failed } = useSignedImage(item.id);
  return (
    <a className="row" href={url || undefined} target="_blank" rel="noreferrer">
      <span className="thumb">{url ? <img src={url} alt="" loading="lazy" onError={failed} /> : <span className="tile-state">{error ? "!" : ""}</span>}</span>
      <span className="row-name">{item.name}</span>
      <span className="row-meta">{item.ratio ? item.ratio + " · " : ""}{age(item.created_at)}</span>
    </a>
  );
}

export default function Gallery({ version }: { version: number }) {
  const [order, setOrder] = useState<Order>(() => remembered("muse-gallery-order", orders.map(o => o[0]), "newest"));
  const [view, setView] = useState<View>(() => remembered("muse-gallery-view", ["grid", "list"] as const, "grid"));
  const [items, setItems] = useState<GalleryItem[] | null>(null);
  const [next, setNext] = useState<number | null>(null);
  const [error, setError] = useState("");
  const [menu, setMenu] = useState(false);
  const loaded = useRef(0);
  const root = useRef<HTMLDivElement>(null);
  const trigger = useRef<HTMLButtonElement>(null);

  const load = useCallback(async (reset: boolean) => {
    try {
      const size = reset ? Math.min(100, Math.max(40, loaded.current)) : 40;
      const data = await api<GalleryData>("/outputs?order=" + order + "&limit=" + size + "&offset=" + (reset ? 0 : loaded.current));
      setItems(previous => {
        const merged = reset || !previous ? data.items : [...previous, ...data.items.filter(n => !previous.some(o => o.id === n.id))];
        loaded.current = merged.length;
        return merged;
      });
      setNext(data.next_offset);
      setError("");
    } catch (e) {
      setError((e as Error).message);
    }
  }, [order]);

  useEffect(() => { load(true); }, [load, version]);

  useEffect(() => {
    if (!menu) return;
    const outside = (event: MouseEvent) => { if (!root.current?.contains(event.target as Node)) setMenu(false); };
    document.addEventListener("mousedown", outside);
    root.current?.querySelector<HTMLElement>('[role="menuitemradio"][aria-checked="true"]')?.focus();
    return () => document.removeEventListener("mousedown", outside);
  }, [menu]);

  function pick(value: Order) {
    setOrder(value);
    try { localStorage.setItem("muse-gallery-order", value); } catch {}
    setMenu(false);
    trigger.current?.focus();
  }

  function changeView(value: View) {
    setView(value);
    try { localStorage.setItem("muse-gallery-view", value); } catch {}
  }

  function keys(event: KeyboardEvent<HTMLDivElement>) {
    if (event.key === "Escape") { event.stopPropagation(); setMenu(false); trigger.current?.focus(); return; }
    if (event.key !== "ArrowDown" && event.key !== "ArrowUp") return;
    event.preventDefault();
    const entries = Array.from(event.currentTarget.querySelectorAll<HTMLElement>('[role="menuitemradio"]'));
    const index = entries.indexOf(document.activeElement as HTMLElement);
    entries[(index + (event.key === "ArrowDown" ? 1 : -1) + entries.length) % entries.length]?.focus();
  }

  const current = orders.find(o => o[0] === order)![1];

  return (
    <>
      <div className="toolbar">
        <div className="menu-wrap" ref={root}>
          <button type="button" ref={trigger} aria-haspopup="menu" aria-expanded={menu} aria-label={"Orden: " + current} onClick={() => setMenu(!menu)}>
            <Action icon="ordenar">{current}</Action>
          </button>
          {menu && (
            <div className="menu" role="menu" aria-label="Orden" onKeyDown={keys}>
              {orders.map(([value, label]) => (
                <button type="button" key={value} role="menuitemradio" aria-checked={order === value} onClick={() => pick(value)}>
                  <span>{label}</span>{order === value && <Icon name="check" />}
                </button>
              ))}
            </div>
          )}
        </div>
        <div className="view-toggle">
          <button type="button" className="icon-btn" aria-label="Cuadrícula" aria-pressed={view === "grid"} onClick={() => changeView("grid")}><Icon name="cuadricula" /></button>
          <button type="button" className="icon-btn" aria-label="Lista" aria-pressed={view === "list"} onClick={() => changeView("list")}><Icon name="lista" /></button>
        </div>
      </div>
      {error && !items && (
        <div className="empty"><h2>No se pudo cargar la galería.</h2><p>{error}</p><button type="button" onClick={() => load(true)}><Action icon="refrescar">Reintentar</Action></button></div>
      )}
      {!items && !error && <ul className="tiles" aria-hidden="true">{Array.from({ length: 8 }, (_, i) => <li key={i}><span className="tile skeleton" /></li>)}</ul>}
      {items && items.length === 0 && <Empty title="Tu galería está vacía." text="Las imágenes terminadas aparecerán aquí." icon="archivos" />}
      {items && items.length > 0 && (view === "grid"
        ? <ul className="tiles">{items.map(item => <li key={item.id}><Tile item={item} /></li>)}</ul>
        : <ul className="rows">{items.map(item => <li key={item.id}><Row item={item} /></li>)}</ul>)}
      {items && next !== null && <button type="button" className="more" onClick={() => load(false)}><Action icon="chevron-abajo">Ver más</Action></button>}
    </>
  );
}
