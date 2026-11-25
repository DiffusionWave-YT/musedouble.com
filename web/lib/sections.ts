export type Section = { id: string; path: string; name: string; icon: string; tone: string };
export type Group = { label?: string; items: Section[] };

export const studioGroups: Group[] = [{
  items: [
    { id: "generate", path: "/image-generation", name: "Generación de imagen", icon: "imagen", tone: "coral" },
    { id: "reference", path: "/image-from-reference", name: "Imagen desde referencia", icon: "mejorar", tone: "morado" },
    { id: "gallery", path: "/gallery", name: "Galería", icon: "archivos", tone: "ambar" },
  ],
}];

export const adminBase = "/" + (process.env.NEXT_PUBLIC_ADMIN_PATH || "admin-local");

export const adminGroups: Group[] = [
  { items: [{ id: "overview", path: adminBase, name: "Vista general", icon: "inicio", tone: "azul" }] },
  {
    label: "Contenido",
    items: [
      { id: "characters", path: adminBase + "/characters", name: "Personajes", icon: "agente", tone: "morado" },
      { id: "workflows", path: adminBase + "/workflows", name: "Workflows", icon: "flujos", tone: "verdeazulado" },
    ],
  },
  {
    label: "Comunidad",
    items: [
      { id: "users", path: adminBase + "/users", name: "Usuarios", icon: "cuenta", tone: "azul" },
      { id: "generations", path: adminBase + "/generations", name: "Generaciones", icon: "imagen", tone: "coral" },
      { id: "codes", path: adminBase + "/codes", name: "Códigos de canje", icon: "estrella", tone: "ambar" },
    ],
  },
  {
    label: "Sistema",
    items: [
      { id: "gpus", path: adminBase + "/servers", name: "Servidores", icon: "progreso", tone: "verdeazulado" },
      { id: "audit", path: adminBase + "/activity", name: "Actividad", icon: "reloj", tone: "gris" },
    ],
  },
];

const permissionKeys: Record<string, string> = { gpus: "servers" };
export const permissionOf = (id: string) => permissionKeys[id] ?? id;
export const allowedSection = (id: string, permissions: string[]) =>
  id === "overview" ? permissions.some(p => p !== "studio") : permissions.includes(permissionOf(id));

export const studioAccount: Section = { id: "account", path: "/account", name: "Mi cuenta", icon: "cuenta", tone: "azul" };
export const adminAccount: Section = { id: "account", path: adminBase + "/account", name: "Mi cuenta", icon: "cuenta", tone: "azul" };

export const studioSlugs = ["image-generation", "image-from-reference", "gallery", "account", "login"];
export const studioHome = "/image-generation";
export const adminSlugs = ["characters", "workflows", "users", "generations", "codes", "servers", "activity", "account", "login"];
export const usersPath = adminBase + "/users";
