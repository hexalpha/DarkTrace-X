/** @type {import('next').NextConfig} */
const nextConfig = {
  // Next's standalone tracer uses symlinks unsupported by some Windows developer environments.
  // Docker sets this flag so the production Linux image still receives the standalone server.
  output: process.env.DOCKER_BUILD === "true" ? "standalone" : undefined,
  poweredByHeader: false,
  reactStrictMode: true,
  typedRoutes: true
};

export default nextConfig;
