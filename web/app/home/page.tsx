import type { Metadata } from "next";
import Presentation from "../../components/Presentation";

export const metadata: Metadata = {
  title: "MuseDouble · Tus ideas, tu imagen",
  description: "Crea más contenido con tu modelo personal de IA y recupera tu tiempo.",
};

export default function Page() {
  return <Presentation />;
}
