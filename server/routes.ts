import type { Express } from "express";
import type { Server } from "http";
import { setupBot, isBotRunning } from "./bot";

export async function registerRoutes(
  httpServer: Server,
  app: Express
): Promise<Server> {
  
  app.get("/api/bot/status", async (req, res) => {
    const uptime = process.uptime();
    res.json({ online: isBotRunning(), uptime });
  });

  try {
    if (process.env.TELEGRAM_BOT_TOKEN) {
      await setupBot();
      console.log("Telegram bot setup successfully");
    } else {
      console.log("Skipping bot setup: TELEGRAM_BOT_TOKEN not found");
    }
  } catch (err) {
    console.error("Failed to setup bot:", err);
  }

  return httpServer;
}
