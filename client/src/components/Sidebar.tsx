import { Link, useLocation } from "wouter";
import { LayoutDashboard, Bot } from "lucide-react";
import { cn } from "@/lib/utils";
import { useBotStatus } from "@/hooks/use-api";

const NAV_ITEMS = [
  { label: "Dashboard", href: "/", icon: LayoutDashboard },
];

export function Sidebar() {
  const [location] = useLocation();
  const { data: status } = useBotStatus();
  const isOnline = status?.online ?? false;

  return (
    <aside className="fixed left-0 top-0 h-screen w-64 bg-card/50 backdrop-blur-xl border-r border-border flex flex-col z-50">
      <div className="p-6 border-b border-border/50 flex items-center gap-3">
        <div className="w-10 h-10 rounded-md bg-primary/20 flex items-center justify-center text-primary">
          <Bot className="w-6 h-6" />
        </div>
        <div>
          <h1 className="font-bold text-lg leading-tight tracking-tight">Netflix Bot</h1>
          <p className="text-xs text-muted-foreground font-mono">Profile Manager</p>
        </div>
      </div>

      <nav className="flex-1 p-4 space-y-2">
        {NAV_ITEMS.map((item) => {
          const isActive = location === item.href;
          return (
            <Link key={item.href} href={item.href}>
              <div
                data-testid={`link-${item.label.toLowerCase()}`}
                className={cn(
                  "flex items-center gap-3 px-4 py-3 rounded-md transition-all duration-200 group cursor-pointer",
                  isActive
                    ? "bg-primary text-primary-foreground font-medium"
                    : "text-muted-foreground hover-elevate"
                )}
              >
                <item.icon className={cn("w-5 h-5", isActive ? "text-primary-foreground" : "text-muted-foreground group-hover:text-foreground")} />
                {item.label}
              </div>
            </Link>
          );
        })}
      </nav>

      <div className="p-4 border-t border-border/50">
        <div className="flex items-center gap-3" data-testid="status-bot">
          <div className={cn(
            "w-2 h-2 rounded-full",
            isOnline ? "bg-green-500 animate-pulse" : "bg-red-500"
          )} />
          <span className={cn(
            "text-xs font-mono",
            isOnline ? "text-green-500" : "text-red-500"
          )}>
            {isOnline ? "BOT RUNNING" : "BOT OFFLINE"}
          </span>
        </div>
      </div>
    </aside>
  );
}
