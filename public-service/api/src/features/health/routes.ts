import { FastifyPluginAsync } from 'fastify';
import { checkConnection } from '../../lib/database.js';

export const healthRoutes: FastifyPluginAsync = async (app) => {
  app.get('', async () => ({
    status: 'healthy',
    service: 'public-api',
  }));

  app.get('/ready', async () => {
    const dbConnected = await checkConnection();

    return {
      status: dbConnected ? 'ready' : 'degraded',
      checks: {
        database: dbConnected ? 'ok' : 'error',
      },
    };
  });
};
