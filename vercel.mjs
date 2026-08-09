const rawBackend = process.env.COCOAID_BACKEND_URL;
if (!rawBackend) {
  throw new Error('COCOAID_BACKEND_URL is required. Set it to your Render backend URL, e.g. https://cocoaid-backend.onrender.com');
}
const backend = rawBackend.replace(/\/+$/, '');
if (!/^https:\/\//i.test(backend)) {
  throw new Error('COCOAID_BACKEND_URL must use https://');
}

export const config = {
  buildCommand: 'node scripts/build_vercel_frontend.mjs',
  outputDirectory: 'vercel_dist',
  cleanUrls: false,
  rewrites: [
    { source: '/api/:path*', destination: `${backend}/api/:path*` },
    { source: '/weather-viewer', destination: '/static/weather-viewer/index.html' }
  ],
  headers: [
    {
      source: '/static/:path*',
      headers: [
        { key: 'Cache-Control', value: 'public, max-age=3600, stale-while-revalidate=86400' }
      ]
    }
  ]
};
