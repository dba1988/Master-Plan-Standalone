import { FastifyReply } from 'fastify';

/**
 * SSE message format.
 */
export interface SSEMessage {
  event?: string;
  data: string;
  id?: string;
  retry?: number;
}

/**
 * Format an SSE message.
 */
export function formatSSE(message: SSEMessage): string {
  let output = '';

  if (message.id) {
    output += `id: ${message.id}\n`;
  }

  if (message.event) {
    output += `event: ${message.event}\n`;
  }

  if (message.retry) {
    output += `retry: ${message.retry}\n`;
  }

  output += `data: ${message.data}\n\n`;

  return output;
}

/**
 * Send SSE headers.
 */
export function sendSSEHeaders(reply: FastifyReply): void {
  reply.raw.writeHead(200, {
    'Content-Type': 'text/event-stream',
    'Cache-Control': 'no-store',
    'Connection': 'keep-alive',
    'X-Accel-Buffering': 'no',
  });
}

/**
 * Send an SSE message.
 */
export function sendSSE(reply: FastifyReply, message: SSEMessage): void {
  reply.raw.write(formatSSE(message));
}

/**
 * Send a ping to keep connection alive.
 */
export function sendPing(reply: FastifyReply): void {
  sendSSE(reply, {
    event: 'ping',
    data: JSON.stringify({ time: Date.now() }),
  });
}
