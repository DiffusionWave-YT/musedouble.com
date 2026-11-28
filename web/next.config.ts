import type { NextConfig } from "next";
const development = process.env.NODE_ENV === "development";
const adminPath = process.env.NEXT_PUBLIC_ADMIN_PATH || (development ? "admin-local" : "");
if (!adminPath) throw new Error("Define NEXT_PUBLIC_ADMIN_PATH en web/.env.local con la ruta secreta del panel.");
const config: NextConfig = {
  poweredByHeader: false,
  devIndicators: false,
  async redirects() {
    return [
      { source: "/admin", destination: "/404", permanent: false },
      { source: "/admin/:path*", destination: "/404", permanent: false },
      { source: "/", destination: "/image-generation", permanent: false },
      { source: "/crear", destination: "/image-generation", permanent: false },
      { source: "/referencia", destination: "/image-from-reference", permanent: false },
      { source: "/galeria", destination: "/gallery", permanent: false },
      { source: "/cuenta", destination: "/account", permanent: false },
    ];
  },
  async rewrites() {
    return {
      beforeFiles: [
        { source: "/" + adminPath, destination: "/admin" },
        { source: "/" + adminPath + "/:path*", destination: "/admin/:path*" },
      ],
      afterFiles: [
        { source: "/api/v1/:path*", destination: "http://127.0.0.1:8010/api/v1/:path*" },
        { source: "/objects/:path*", destination: "http://127.0.0.1:9011/objects/:path*" },
      ],
      fallback: [],
    };
  },
  async headers() {
    return [{ source: "/:path*", headers: [
      {key:"X-Content-Type-Options",value:"nosniff"},
      {key:"Referrer-Policy",value:"no-referrer"},
      {key:"X-Frame-Options",value:"DENY"},
      {key:"Permissions-Policy",value:"camera=(), microphone=(), geolocation=()"},
      {key:"Content-Security-Policy",value:`default-src 'self'; script-src 'self' 'unsafe-inline' https://challenges.cloudflare.com${development?" 'unsafe-eval'":""}; style-src 'self' 'unsafe-inline'; img-src 'self' blob:${development?" http://127.0.0.1:9011":""}; frame-src https://challenges.cloudflare.com; connect-src 'self'${development?" ws://127.0.0.1:8010 ws://127.0.0.1:3001":""}; object-src 'none'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'`}
    ]}];
  }
};
export default config;
