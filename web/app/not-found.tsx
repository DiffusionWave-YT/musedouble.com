import Link from "next/link";
import { Action, Brand } from "../components/ui";

export default function NotFound() {
  return (
    <main className="notfound">
      <Brand />
      <h1>No encontramos esta página.</h1>
      <nav className="notfound-links" aria-label="Destinos">
        <Link href="/crear" className="primary link-button"><Action icon="inicio">Volver al estudio</Action></Link>
        <Link href="/galeria" className="link-button secondary"><Action icon="archivos">Galería</Action></Link>
      </nav>
    </main>
  );
}
