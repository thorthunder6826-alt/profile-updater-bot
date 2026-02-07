import { Telegraf } from "telegraf";
import { storage } from "./storage";

let bot: Telegraf;

export async function setupBot() {
  if (!process.env.TELEGRAM_BOT_TOKEN) {
    throw new Error("TELEGRAM_BOT_TOKEN must be set");
  }

  bot = new Telegraf(process.env.TELEGRAM_BOT_TOKEN);

  bot.start(async (ctx) => {
    const telegramId = ctx.from.id.toString();
    const username = ctx.from.username;

    let user = await storage.getUserByTelegramId(telegramId);
    if (!user) {
      user = await storage.createUser({
        telegramId,
        username,
      });
    }

    ctx.reply("Welcome to Netflix Profile Updater Bot! \nUse /login <email> <password> to set your credentials.");
    await storage.createLog({
      telegramId,
      action: "start",
      status: "success",
      details: "User started bot",
    });
  });

  bot.command("login", async (ctx) => {
    const parts = ctx.message.text.split(" ");
    if (parts.length !== 3) {
      return ctx.reply("Usage: /login <email> <password>");
    }

    const [_, email, password] = parts;
    const telegramId = ctx.from.id.toString();

    let user = await storage.getUserByTelegramId(telegramId);
    if (user) {
      await storage.updateUser(user.id, {
        netflixEmail: email,
        netflixPassword: password,
        isLoggedIn: true,
      });
    }

    ctx.reply("Credentials saved! (Simulated) \nUse /update_profile <name> to update your profile name.");
    await storage.createLog({
      telegramId,
      action: "login",
      status: "success",
      details: "User updated credentials",
    });
  });

  bot.command("update_profile", async (ctx) => {
    const parts = ctx.message.text.split(" ");
    if (parts.length < 2) {
      return ctx.reply("Usage: /update_profile <name>");
    }

    const name = parts.slice(1).join(" ");
    const telegramId = ctx.from.id.toString();

    // Here we would call the actual Netflix automation logic
    // For now, we simulate a delay and success
    ctx.reply(`Updating profile to "${name}"... please wait.`);

    setTimeout(async () => {
       ctx.reply(`Successfully updated profile name to "${name}"!`);
       await storage.createLog({
         telegramId,
         action: "update_profile",
         status: "success",
         details: `Updated profile name to ${name}`,
       });
    }, 2000);
  });

  bot.launch().catch(err => {
    console.error("Bot launch failed:", err);
  });

  // Enable graceful stop
  process.once('SIGINT', () => bot.stop('SIGINT'));
  process.once('SIGTERM', () => bot.stop('SIGTERM'));
}
