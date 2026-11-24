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
    label: "Contenido",
    items: [
      { id: "characters", path: base + "/personajes", name: "Personajes", icon: "agente", tone: "morado" },
      { id: "workflows", path: base + "/workflows", name: "Workflows", icon: "flujos", tone: "verdeazulado" },
    ],
  },
  {
    label: "Comunidad",
    items: [
      { id: "users", path: base + "/usuarios", name: "Usuarios", icon: "cuenta", tone: "azul" },
      { id: "generations", path: base + "/generaciones", name: "Generaciones", icon: "imagen", tone: "coral" },
    ],
  },
  {
    label: "Sistema",
    items: [
      { id: "gpus", path: base + "/servidores", name: "Servidores", icon: "progreso", tone: "verdeazulado" },
      { id: "audit", path: base + "/actividad", name: "Actividad", icon: "reloj", tone: "gris" },
    ],
  },
];

export const studioAccount: Section = { id: "account", path: "/cuenta", name: "Mi cuenta", icon: "cuenta", tone: "azul" };
export const adminAccount: Section = { id: "account", path: base + "/cuenta", name: "Mi cuenta", icon: "cuenta", tone: "azul" };

export const studioSlugs = ["crear", "referencia", "galeria", "cuenta"];
export const adminSlugs = ["personajes", "workflows", "usuarios", "generaciones", "servidores", "actividad", "cuenta"];
export const usersPath = base + "/usuarios";
