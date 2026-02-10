import 'dotenv/config';

export const config = {
  // Server
  port: parseInt(process.env.PORT || '8001', 10),
  host: process.env.HOST || '0.0.0.0',

  // Database (read-only)
  databaseUrl: process.env.DATABASE_URL || 'postgres://readonly:readonly@localhost:5432/masterplan',

  // CDN
  cdnBaseUrl: process.env.CDN_BASE_URL || 'https://cdn.example.com',

  // Client API (external)
  clientApiUrl: process.env.CLIENT_API_URL,
  clientApiKey: process.env.CLIENT_API_KEY,
  clientApiTimeout: parseInt(process.env.CLIENT_API_TIMEOUT || '10000', 10),

  // App settings
  debug: process.env.DEBUG === 'true',
} as const;
