import { z } from 'zod';
import { logs, users } from './schema';

export const api = {
  bot: {
    status: {
      method: 'GET' as const,
      path: '/api/bot/status' as const,
      responses: {
        200: z.object({
          online: z.boolean(),
          uptime: z.number(),
          userCount: z.number(),
        }),
      },
    },
    logs: {
      method: 'GET' as const,
      path: '/api/bot/logs' as const,
      responses: {
        200: z.array(z.custom<typeof logs.$inferSelect>()),
      },
    },
  },
};
