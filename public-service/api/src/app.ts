import Fastify from 'fastify';
import cors from '@fastify/cors';
import { config } from './lib/config.js';
import { healthRoutes } from './features/health/routes.js';
import { releaseRoutes } from './features/release/routes.js';
import { statusRoutes } from './features/status/routes.js';

export async function buildApp() {
  const app = Fastify({
    logger: config.debug,
  });

  // CORS - allow all origins for public API
  await app.register(cors, {
    origin: '*',
    credentials: false,
    methods: ['GET', 'HEAD', 'OPTIONS'],
  });

  // Routes
  await app.register(healthRoutes, { prefix: '/health' });
  await app.register(releaseRoutes, { prefix: '/api/releases' });
  await app.register(statusRoutes, { prefix: '/api/status' });

  // Root
  app.get('/', async () => ({
    service: 'Master Plan Public API',
    status: 'ok',
  }));

  return app;
}
