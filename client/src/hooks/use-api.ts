import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { type User, type Log, type InsertUser } from "@shared/schema";
import { apiRequest } from "@/lib/queryClient";

// ============================================
// USERS HOOKS
// ============================================

export function useUsers() {
  return useQuery<User[]>({
    queryKey: ["/api/users"],
    // In a real app, we would fetch from the API
    // For now, we'll try to fetch, but fallback to mock data if the backend isn't ready
    queryFn: async () => {
      try {
        const res = await fetch("/api/users");
        if (!res.ok) throw new Error("Failed to fetch users");
        return await res.json();
      } catch (e) {
        console.warn("Using mock users data");
        return MOCK_USERS;
      }
    },
  });
}

export function useCreateUser() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (user: InsertUser) => {
      const res = await apiRequest("POST", "/api/users", user);
      return await res.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["/api/users"] });
    },
  });
}

export function useDeleteUser() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => {
      await apiRequest("DELETE", `/api/users/${id}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["/api/users"] });
    },
  });
}

// ============================================
// LOGS HOOKS
// ============================================

export function useLogs() {
  return useQuery<Log[]>({
    queryKey: ["/api/logs"],
    queryFn: async () => {
      try {
        const res = await fetch("/api/logs");
        if (!res.ok) throw new Error("Failed to fetch logs");
        return await res.json();
      } catch (e) {
        console.warn("Using mock logs data");
        return MOCK_LOGS;
      }
    },
  });
}

// ============================================
// MOCK DATA (Fallback)
// ============================================

const MOCK_USERS: User[] = [
  { id: 1, telegramId: "123456789", username: "alex_dev", netflixEmail: "alex@example.com", netflixPassword: "***", isLoggedIn: true, lastActive: new Date().toISOString() as any },
  { id: 2, telegramId: "987654321", username: "sarah_watcher", netflixEmail: "sarah@test.com", netflixPassword: "***", isLoggedIn: false, lastActive: new Date(Date.now() - 86400000).toISOString() as any },
  { id: 3, telegramId: "456123789", username: "movie_buff_99", netflixEmail: "buff@movies.com", netflixPassword: "***", isLoggedIn: true, lastActive: new Date(Date.now() - 3600000).toISOString() as any },
];

const MOCK_LOGS: Log[] = [
  { id: 1, telegramId: "123456789", action: "PROFILE_UPDATE", status: "success", details: "Changed profile icon to Monkey", createdAt: new Date().toISOString() as any },
  { id: 2, telegramId: "987654321", action: "LOGIN_ATTEMPT", status: "failed", details: "Invalid password provided", createdAt: new Date(Date.now() - 1000 * 60 * 5).toISOString() as any },
  { id: 3, telegramId: "456123789", action: "PROFILE_UPDATE", status: "success", details: "Changed profile name", createdAt: new Date(Date.now() - 1000 * 60 * 30).toISOString() as any },
  { id: 4, telegramId: "123456789", action: "BOT_COMMAND", status: "success", details: "/start command received", createdAt: new Date(Date.now() - 1000 * 60 * 60).toISOString() as any },
  { id: 5, telegramId: "987654321", action: "LOGOUT", status: "success", details: "User requested logout", createdAt: new Date(Date.now() - 1000 * 60 * 120).toISOString() as any },
];
