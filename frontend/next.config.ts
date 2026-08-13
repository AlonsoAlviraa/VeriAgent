import type { NextConfig } from "next";

/**
 * Do NOT rewrite /api/v1 here.
 * Array rewrites run after static files and BEFORE dynamic App routes, so
 * they steal /api/v1/:path* from app/api/v1/[...path]/route.ts and can drop
 * ?wait= and X-Tenant-Id. The route handler is the only browser → API proxy.
 */
const nextConfig: NextConfig = {};

export default nextConfig;
