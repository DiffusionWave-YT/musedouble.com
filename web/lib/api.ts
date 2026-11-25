import type { components } from "../generated/api";
export type User = components["schemas"]["UserOut"];
export type Session = components["schemas"]["SessionOut"];
export type Catalog = components["schemas"]["CatalogOut"];
export type Job = components["schemas"]["JobOut"];
export type Jobs = components["schemas"]["JobListOut"];
export type JobCreate = components["schemas"]["JobCreate"];
export type Model = components["schemas"]["ModelInput"];
export type Gallery = components["schemas"]["GalleryOut"];
export type GalleryItem = components["schemas"]["GalleryItem"];
export type SignedUrl = components["schemas"]["SignedUrlOut"];
export type GenerationLimits = components["schemas"]["GenerationSettings"];
import { tr } from "./i18n";
let csrf = "";
export function setCsrf(token:string){csrf=token;}
export async function api<T>(path:string, options:RequestInit={}):Promise<T>{
  const headers = new Headers(options.headers);
  if(options.body && !(options.body instanceof FormData)) headers.set("Content-Type","application/json");
  if(options.method && options.method!=="GET") headers.set("X-CSRF-Token",csrf);
  const r = await fetch("/api/v1"+path,{...options,headers,credentials:"include",cache:"no-store"});
  const data=await r.json();
  if(!r.ok) throw Object.assign(new Error(tr(typeof data.detail==="string"?data.detail:"No se pudo completar la solicitud.")),{status:r.status});
  return data as T;
}
