import type { Express } from "express";
import type { Server } from "http";
import { storage } from "./storage";
import { api } from "@shared/routes";
import { setupBot } from "./bot";

export async function registerRoutes(
  httpServer: Server,
  app: Express
): Promise<Server> {
  
  // API Routes
  app.get(api.bot.status.path, async (req, res) => {
    const userCount = await storage.getUserCount();
    const uptime = process.uptime();
    res.json({ online: true, uptime, userCount });
  });

  app.get(api.bot.logs.path, async (req, res) => {
    const logs = await storage.getLogs();
    res.json(logs);
  });

  // Setup Telegram Bot
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
