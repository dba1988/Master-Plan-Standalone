import { FastifyPluginAsync } from 'fastify';
import { statusService } from './service.js';
import { sendSSEHeaders, sendSSE, sendPing } from '../../lib/sse.js';
import type { StatusResponse } from './types.js';

interface SlugParams {
  slug: string;
}

interface OverlayParams extends SlugParams {
  overlayId: string;
}

export const statusRoutes: FastifyPluginAsync = async (app) => {
  /**
   * GET /api/status/:slug/stream
   * SSE stream for real-time status updates.
   * NOTE: Must be registered before /:slug/:overlayId to avoid route conflict.
   */
  app.get<{ Params: SlugParams }>('/:slug/stream', async (request, reply) => {
    const { slug } = request.params;

    // Set up SSE headers
    sendSSEHeaders(reply);

    // Send initial connection event
    sendSSE(reply, {
      event: 'connected',
      data: JSON.stringify({ project: slug }),
    });

    // Send initial statuses
    const initialStatuses = await statusService.getStatuses(slug);
    sendSSE(reply, {
      event: 'status_update',
      data: JSON.stringify({ statuses: initialStatuses }),
    });

    // Set up polling interval
    let lastStatuses = JSON.stringify(initialStatuses);

    const pollInterval = setInterval(async () => {
      try {
        const statuses = await statusService.getStatuses(slug);
        const statusesJson = JSON.stringify(statuses);

        // Only send if changed
        if (statusesJson !== lastStatuses) {
          sendSSE(reply, {
            event: 'status_update',
            data: JSON.stringify({ statuses }),
          });
          lastStatuses = statusesJson;
        }
      } catch (error) {
        // Silently continue on errors
      }
    }, 5000);

    // Set up keepalive ping
    const pingInterval = setInterval(() => {
      sendPing(reply);
    }, 30000);

    // Cleanup on disconnect
    request.raw.on('close', () => {
      clearInterval(pollInterval);
      clearInterval(pingInterval);
    });

    // Don't close the response - keep it open for SSE
    return reply;
  });

  /**
   * POST /api/status/:slug/refresh
   * Force refresh statuses from client API.
   */
  app.post<{ Params: SlugParams }>('/:slug/refresh', async (request, reply) => {
    const { slug } = request.params;

    const statuses = await statusService.refreshStatuses(slug);

    reply.header('Cache-Control', 'no-store');

    return {
      project: slug,
      statuses,
      count: Object.keys(statuses).length,
      refreshed_at: new Date().toISOString(),
    };
  });

  /**
   * GET /api/status/:slug
   * Returns all overlay statuses for a project.
   */
  app.get<{ Params: SlugParams }>('/:slug', async (request, reply) => {
    const { slug } = request.params;

    const statuses = await statusService.getStatuses(slug);

    reply.header('Cache-Control', 'no-store');

    const response: StatusResponse = {
      project: slug,
      statuses,
      count: Object.keys(statuses).length,
    };

    return response;
  });

  /**
   * GET /api/status/:slug/:overlayId
   * Returns status for a specific overlay.
   * NOTE: Must be registered after /:slug/stream to avoid route conflict.
   */
  app.get<{ Params: OverlayParams }>('/:slug/:overlayId', async (request, reply) => {
    const { slug, overlayId } = request.params;

    const status = await statusService.getOverlayStatus(slug, overlayId);

    reply.header('Cache-Control', 'no-store');

    return {
      project: slug,
      overlay_id: overlayId,
      status,
      updated_at: new Date().toISOString(),
    };
  });
};
