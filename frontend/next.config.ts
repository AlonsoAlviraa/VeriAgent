import type { NextConfig } from "next";

const backend =
  process.env.BACKEND_URL ||
  process.env.API_PROXY_TARGET ||
  "http://localhost:8000";

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      {
        source: "/api/v1/:path*",
        destination: `${backend.replace(/\/$/, "")}/api/v1/:path*`,
      },
    ];
  },
};

export default nextConfig;
