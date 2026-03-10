import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  images: {
    remotePatterns: [
      { hostname: "ddragon.leagueoflegends.com" },
    ],
  },
};

export default nextConfig;
