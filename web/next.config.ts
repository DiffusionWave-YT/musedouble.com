import type { NextConfig } from "next";
const development = process.env.NODE_ENV === "development";
const config: NextConfig = {
  poweredByHeader: false,
  devIndicators: false,
  async rewrites() {
    return [{ source: "/api/v1/:path*", destination: "http://127.0.0.1:8010/api/v1/:path*" }];
  },
  async headers() {
    return [{ source: "/:path*", headers: [
      {key:"X-Content-Type-Options",value:"nosniff"},
      {key:"Referrer-Policy",value:"no-referrer"},
      {key:"X-Frame-Options",value:"DENY"},
      {key:"Permissions-Policy",value:"camera=(), microphone=(), geolocation=()"},
      {key:"Content-Security-Policy",value:`default-src 'self'; script-src 'self' 'unsafe-inline'${development?" 'unsafe-eval'":""}; style-src 'self' 'unsafe-inline'; img-src 'self' blob: http://127.0.0.1:9011; connect-src 'self'${development?" ws://127.0.0.1:3001":""}; object-src 'none'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'`}
    ]}];
  }
};
export default config;
