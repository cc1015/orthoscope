/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Emit a self-contained server bundle so the Docker image does not need to
  // ship node_modules. No effect on `next dev`.
  output: "standalone",
};

export default nextConfig;
