export function resolveApiBaseUrl(configuredUrl, isProduction) {
  const value = typeof configuredUrl === 'string' ? configuredUrl.trim() : '';
  if (!value) {
    if (!isProduction) return '/api';
    throw new Error(
      'The production backend URL is not configured. Set VITE_API_BASE_URL in Vercel to the deployed FastAPI base URL ending in /api, then redeploy.',
    );
  }

  if (!isProduction) return value.replace(/\/+$/, '');

  let parsed;
  try {
    parsed = new URL(value);
  } catch {
    throw new Error('VITE_API_BASE_URL must be an absolute HTTPS URL ending in /api.');
  }

  if (
    parsed.protocol !== 'https:'
    || !parsed.pathname.replace(/\/+$/, '').endsWith('/api')
    || parsed.username
    || parsed.password
    || parsed.search
    || parsed.hash
    || ['localhost', '127.0.0.1', '0.0.0.0', '::1'].includes(parsed.hostname)
  ) {
    throw new Error(
      'VITE_API_BASE_URL must be a public HTTPS backend URL ending in /api; localhost and relative URLs are not valid in production.',
    );
  }

  return `${parsed.origin}${parsed.pathname.replace(/\/+$/, '')}`;
}
