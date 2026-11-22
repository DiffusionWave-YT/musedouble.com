export type Section = { id: string; path: string; name: string; icon: string; tone: string };
export type Group = { label?: string; items: Section[] };

export const studioGroups: Group[] = [{
  items: [
    { id: "generate", path: "/crear", name: "Crear imagen", icon: "imagen", tone: "coral" },
    { id: "reference", path: "/referencia", name: "Usar referencia", icon: "mejorar", tone: "morado" },
    { id: "gallery", path: "/galeria", name: "Galería", icon: "archivos", tone: "ambar" },
  ],
}];

const base = "/control-musedouble";

export const adminGroups: Group[] = [
  { items: [{ id: "overview", path: base, name: "Vista general", icon: "inicio", tone: "azul" }] },
  {
    label: "Administración",
    items: [
      { id: "models", path: base + "/modelos", name: "Modelos", icon: "agente", tone: "morado" },
      { id: "workflows", path: base + "/workflows", name: "Workflows", icon: "flujos", tone: "verdeazulado" },
      { id: "gpus", path: base + "/servidores", name: "Servidores", icon: "progreso", tone: "verdeazulado" },
      { id: "users", path: base + "/usuarios", name: "Usuarios y créditos", icon: "cuenta", tone: "azul" },
      { id: "audit", path: base + "/actividad", name: "Actividad", icon: "reloj", tone: "gris" },
    ],
  },
];

export const studioAccount: Section = { id: "account", path: "/cuenta", name: "Mi cuenta", icon: "cuenta", tone: "azul" };
export const adminAccount: Section = { id: "account", path: base + "/cuenta", name: "Mi cuenta", icon: "cuenta", tone: "azul" };

export const studioSlugs = ["crear", "referencia", "galeria", "cuenta"];
export const adminSlugs = ["modelos", "workflows", "servidores", "usuarios", "actividad", "cuenta"];
