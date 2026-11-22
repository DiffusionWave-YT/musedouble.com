import type { Metadata } from "next";
import "./style.css";

export const metadata: Metadata = { title: "MuseDouble", description: "Estudio de creación de imágenes" };

const theme = "try{document.documentElement.dataset.theme=localStorage.getItem('muse-theme')==='dark'?'dark':'light'}catch{document.documentElement.dataset.theme='light'}";

export default function Layout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es" suppressHydrationWarning>
      <head><script dangerouslySetInnerHTML={{ __html: theme }} /></head>
      <body>{children}</body>
    </html>
  );
}
