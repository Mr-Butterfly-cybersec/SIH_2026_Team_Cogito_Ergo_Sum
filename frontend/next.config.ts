import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  /**
   * API requests are proxied by a route handler (src/app/api/[...path]/route.ts) rather than a
   * `rewrites()` rule. Rewrites are evaluated when the config is loaded, which for a standalone
   * build happens at build time — so an env var set at runtime (as Docker Compose does) would be
   * ignored and the destination frozen to the build-time default. A route handler reads the
   * environment per request, so one image works on localhost, behind a tunnel, or deployed.
   */
};

export default nextConfig;
