import { studioSlugs } from "../../../lib/sections";

export const dynamicParams = false;

export function generateStaticParams() {
  return studioSlugs.map(section => ({ section }));
}

export default function Page() {
  return null;
}
