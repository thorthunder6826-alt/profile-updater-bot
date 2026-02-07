import { z } from 'zod';

export const api = {
  bot: {
    status: {
      method: 'GET' as const,
      path: '/api/bot/status' as const,
      responses: {
        200: z.object({
          online: z.boolean(),
          uptime: z.number(),
        }),
      },
    },
  },
};
