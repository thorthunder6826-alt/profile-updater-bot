import { pgTable, text, serial, integer, boolean, timestamp } from "drizzle-orm/pg-core";
import { createInsertSchema } from "drizzle-zod";
import { z } from "zod";

export const users = pgTable("users", {
  id: serial("id").primaryKey(),
  telegramId: text("telegram_id").notNull().unique(),
  username: text("username"),
  isLoggedIn: boolean("is_logged_in").default(false),
  lastActive: timestamp("last_active").defaultNow(),
});

export const insertUserSchema = createInsertSchema(users).omit({ id: true, lastActive: true });

export type User = typeof users.$inferSelect;
export type InsertUser = z.infer<typeof insertUserSchema>;
