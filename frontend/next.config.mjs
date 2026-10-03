/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  async rewrites() {
    const rawApiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
    const destinationBase = rawApiUrl.endsWith("/api/v1")
      ? rawApiUrl
      : `${rawApiUrl.replace(/\/+$/, "")}/api/v1`;
    return [
      {
        source: "/api/v1/:path*",
        destination: `${destinationBase}/:path*`,
      },
    ];
  },
};

export default nextConfig;
