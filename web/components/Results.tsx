"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import { api, type SignedUrl } from "../lib/api";
import { Action } from "./ui";

export function useSignedImage(id: string, scope = "") {
  const [url, setUrl] = useState("");
  const [error, setError] = useState("");
  const renewed = useRef(0);
  const load = useCallback(() => api<SignedUrl>(scope + "/outputs/" + id + "/url").then(x => setUrl(x.url)).catch(e => setError(e.message)), [id, scope]);
  useEffect(() => { load(); }, [load]);
  const failed = () => { if (renewed.current++ < 1) load(); else setError("No se pudo cargar la imagen."); };
  return { url, error, failed };
}

export async function downloadOriginal(id: string) {
  const signed = await api<SignedUrl>("/outputs/" + id + "/url?download=true");
  window.location.assign(signed.url);
}

export function Result({ id, name, mode }: { id: string; name: string; mode: string }) {
  const { url, error, failed } = useSignedImage(id);
  const [downloadError, setDownloadError] = useState("");
  const download = () => downloadOriginal(id).catch(e => setDownloadError(e.message));
  return (
    <figure className="result">
      {url
        ? <a href={url} target="_blank" rel="noreferrer"><img src={url} alt={"Imagen creada con " + name} loading="lazy" onError={failed} /></a>
        : <div className="image-placeholder">{error || "Cargando imagen…"}</div>}
      <figcaption>
        <strong>{name}</strong>
        <small>{mode === "reference" ? "Imagen de referencia" : "Generación de imagen"}</small>
        <button className="text-button" onClick={download}><Action icon="descargar">Descargar original</Action></button>
        {downloadError && <small className="error" role="alert">{downloadError}</small>}
      </figcaption>
    </figure>
  );
}
