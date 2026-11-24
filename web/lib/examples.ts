export type Photo = { file: string; alt: string };
export type Collection = { id: string; label: string; photos: Photo[] };

const make = (id: string, label: string, alt: string, count: number): Collection => ({
  id,
  label,
  photos: Array.from({ length: count }, (_, i) => ({ file: `${id}-${i + 1}`, alt })),
});

export const collections: Record<string, Collection> = {
  selfie: {
    id: "selfie",
    label: "Selfies a pedido",
    photos: [
      { file: "selfie-1", alt: "Selfie sonriendo con el signo de paz" },
      { file: "selfie-2", alt: "Selfie de espejo con censura incorporada" },
    ],
  },
  halloween: make("halloween", "Halloween", "Colección Halloween con vestido negro y capa roja", 4),
  paris: make("paris", "Tú en París", "Colección en París con la Torre Eiffel de noche", 3),
  outdoor: make("outdoor", "Escenarios exteriores", "Colección de exteriores con censura incorporada", 4),
  sunday: make("sunday", "Sunday Morning", "Colección Sunday Morning con vestido blanco y pañuelo azul", 3),
};

export const photoSrc = (file: string) => `/ejemplos/${file}.jpg`;

export function parseHash(hash: string): { id: string; index: number } | null {
  const match = /^#foto-([a-z]+)-(\d+)$/.exec(hash);
  if (!match) return null;
  const set = collections[match[1]];
  const index = Number(match[2]) - 1;
  return set && index >= 0 && index < set.photos.length ? { id: set.id, index } : null;
}
