import type { ReactNode } from "react";

const own = ["cuadricula", "lista", "ordenar"];

export function Icon({ name }: { name: string }) {
  const file = own.includes(name) ? "propios" : "sprite";
  return <svg className="icon" aria-hidden="true" focusable="false"><use href={"/iconos/" + file + ".svg#i-" + name} /></svg>;
}

export function Brand() {
  return <span className="brand"><b aria-hidden="true">m</b><span className="label">MuseDouble</span></span>;
}

export function Empty({ title, text, icon = "imagen" }: { title: string; text: string; icon?: string }) {
  return <div className="empty"><span className="ic-ficha ic-tono-morado" aria-hidden="true"><Icon name={icon} /></span><h2>{title}</h2><p>{text}</p></div>;
}

export function Action({ icon, children }: { icon: string; children: ReactNode }) {
  return <><Icon name={icon} /><span className="label">{children}</span></>;
}
