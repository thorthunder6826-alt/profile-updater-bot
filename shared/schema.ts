import { pgTable, text, serial, integer, boolean, timestamp } from "drizzle-orm/pg-core";
import { createInsertSchema } from "drizzle-zod";
import { z } from "zod";

export const users = pgTable("users", {
  id: serial("id").primaryKey(),
  telegramId: text("telegram_id").notNull().unique(),
  username: text("username"),
  netflixEmail: text("netflix_email"),
  netflixPassword: text("netflix_password"),
  isLoggedIn: boolean("is_logged_in").default(false),
  lastActive: timestamp("last_active").defaultNow(),
});

export const logs = pgTable("logs", {
  id: serial("id").primaryKey(),
  telegramId: text("telegram_id"),
  action: text("action").notNull(),
  status: text("status").notNull(), // 'success', 'failed'
  details: text("details"),
  createdAt: timestamp("created_at").defaultNow(),
});

export const insertUserSchema = createInsertSchema(users).omit({ id: true, lastActive: true });
export const insertLogSchema = createInsertSchema(logs).omit({ id: true, createdAt: true });

export type User = typeof users.$inferSelect;
export type InsertUser = z.infer<typeof insertUserSchema>;
export type Log = typeof logs.$inferSelect;
export type InsertLog = z.infer<typeof insertLogSchema>;
