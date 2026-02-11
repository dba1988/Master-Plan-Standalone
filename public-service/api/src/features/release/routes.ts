import { FastifyPluginAsync } from 'fastify';
import { query } from '../../lib/database.js';
import { config } from '../../lib/config.js';
import type { Project, ReleaseInfo } from './types.js';

interface SlugParams {
  slug: string;
}

export const releaseRoutes: FastifyPluginAsync = async (app) => {
  /**
   * GET /api/releases/:slug/current
   * Redirects to the current release.json on CDN.
   */
  app.get<{ Params: SlugParams }>('/:slug/current', async (request, reply) => {
    const { slug } = request.params;

    const projects = await query<Project>(
      'SELECT current_release_id FROM projects WHERE slug = $1 AND is_active = true',
      [slug]
    );

    if (projects.length === 0) {
      return reply.status(404).send({
        error: 'Project not found or inactive',
      });
    }

    const releaseId = projects[0].current_release_id;
    if (!releaseId) {
      return reply.status(404).send({
        error: 'No published version available',
      });
    }

    const cdnUrl = `${config.cdnBaseUrl}/mp/${slug}/releases/${releaseId}/release.json`;

    reply.header('Cache-Control', 'no-cache');
    reply.header('X-Release-Id', releaseId);

    return reply.redirect(307, cdnUrl);
  });

  /**
   * GET /api/releases/:slug/info
   * Returns release metadata without redirect.
   */
  app.get<{ Params: SlugParams }>('/:slug/info', async (request, reply) => {
    const { slug } = request.params;

    const projects = await query<Project>(
      'SELECT current_release_id FROM projects WHERE slug = $1 AND is_active = true',
      [slug]
    );

    if (projects.length === 0) {
      return reply.status(404).send({
        error: 'Project not found or inactive',
      });
    }

    const releaseId = projects[0].current_release_id;
    if (!releaseId) {
      return reply.status(404).send({
        error: 'No published version available',
      });
    }

    reply.header('Cache-Control', 'no-cache');

    const response: ReleaseInfo = {
      release_id: releaseId,
      cdn_url: `${config.cdnBaseUrl}/mp/${slug}/releases/${releaseId}/release.json`,
      // Tiles are stored under tiles/project/ (primary base map level)
      tiles_base: `${config.cdnBaseUrl}/mp/${slug}/releases/${releaseId}/tiles/project`,
    };

    return response;
  });
};
