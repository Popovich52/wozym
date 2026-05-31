import type { NextConfig } from "next";
import path from "node:path";

const backendProxyUrl = process.env.BACKEND_PROXY_URL ?? "http://127.0.0.1:8617";

const nextConfig: NextConfig = {
  turbopack: {
    root: path.resolve(__dirname, ".."),
  },
  async rewrites() {
    return [
      {
        source: "/backend/:path*",
        destination: `${backendProxyUrl}/:path*`,
      },
    ];
  },
};

export default nextConfig;
