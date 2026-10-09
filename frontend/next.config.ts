import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "export", // static site served from out/ (see wasmer.toml)
  images: {
    unoptimized: true,
  },
};

export default nextConfig;
