import { adminSlugs } from "../../../lib/sections";

export const dynamicParams = false;

export function generateStaticParams() {
  return adminSlugs.map(section => ({ section }));
}

export default function Page() {
  return null;
}
