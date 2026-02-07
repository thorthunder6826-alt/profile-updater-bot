import { useQuery } from "@tanstack/react-query";

interface BotStatus {
  online: boolean;
  uptime: number;
}

export function useBotStatus() {
  return useQuery<BotStatus>({
    queryKey: ["/api/bot/status"],
    refetchInterval: 5000,
  });
}
