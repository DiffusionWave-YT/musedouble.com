"use client";
import Link from "next/link";
import { tr, useLang } from "../lib/i18n";
import { Action, BrandHome, LangToggle } from "../components/ui";

export default function NotFound() {
  useLang();
  return (
    <main className="notfound">
      <div className="corner-tools"><LangToggle /></div>
      <BrandHome />
      <h1>{tr("No encontramos esta página.")}</h1>
      <nav className="notfound-links" aria-label={tr("Destinos")}>
        <Link href="/image-generation" className="primary link-button"><Action icon="inicio">{tr("Volver al estudio")}</Action></Link>
        <Link href="/gallery" className="link-button secondary"><Action icon="archivos">{tr("Galería")}</Action></Link>
      </nav>
    </main>
  );
}
