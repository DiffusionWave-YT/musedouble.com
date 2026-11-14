import type { Metadata } from "next";
import "./style.css";
export const metadata: Metadata = {title:"MuseDouble · Estudio local", description:"Tu estudio de creación"};
const theme = "try{document.documentElement.dataset.theme=localStorage.getItem('muse-theme')==='dark'?'dark':'light'}catch{}";
export default function Layout({children}:{children:React.ReactNode}) {
  return <html lang="es" suppressHydrationWarning><head><script dangerouslySetInnerHTML={{__html:theme}} /></head><body>{children}</body></html>;
}
