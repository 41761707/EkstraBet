import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Wymagane przez produkcyjny obraz Docker (standalone server.js)
  output: "standalone",
  reactStrictMode: true,
  serverExternalPackages: ["@cursor/sdk"],
};

export default nextConfig;
