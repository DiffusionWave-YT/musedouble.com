"use client";
import { useEffect, useRef } from "react";

type Api = { render: (el: HTMLElement, options: Record<string, unknown>) => string; remove: (id: string) => void };
declare global { interface Window { turnstile?: Api } }

const SRC = "https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit";

function ready(): Promise<Api> {
  return new Promise((resolve, reject) => {
    if (window.turnstile) return resolve(window.turnstile);
    let script = document.querySelector<HTMLScriptElement>('script[data-turnstile]');
    if (!script) {
      script = document.createElement("script");
      script.src = SRC;
      script.async = true;
      script.dataset.turnstile = "1";
      document.head.appendChild(script);
    }
    script.addEventListener("load", () => window.turnstile ? resolve(window.turnstile) : reject(new Error("turnstile")));
    script.addEventListener("error", () => reject(new Error("turnstile")));
  });
}

export function Turnstile({ siteKey, onToken, resetKey }: { siteKey: string; onToken: (token: string) => void; resetKey: number }) {
  const box = useRef<HTMLDivElement>(null);
  const callback = useRef(onToken);
  callback.current = onToken;

  useEffect(() => {
    let id = "";
    let gone = false;
    ready().then(api => {
      if (gone || !box.current) return;
      id = api.render(box.current, {
        sitekey: siteKey,
        callback: (token: string) => callback.current(token),
        "expired-callback": () => callback.current(""),
        "error-callback": () => callback.current(""),
      });
    }).catch(() => callback.current(""));
    return () => { gone = true; if (id && window.turnstile) window.turnstile.remove(id); };
  }, [siteKey, resetKey]);

  return <div ref={box} className="captcha" />;
}
