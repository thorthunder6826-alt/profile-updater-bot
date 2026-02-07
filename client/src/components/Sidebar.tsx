import { Link, useLocation } from "wouter";
import { LayoutDashboard, Users, Terminal, Activity, Settings, Bot } from "lucide-react";
import { cn } from "@/lib/utils";

const NAV_ITEMS = [
  { label: "Dashboard", href: "/", icon: LayoutDashboard },
  { label: "Users", href: "/users", icon: Users },
  { label: "Activity Logs", href: "/logs", icon: Terminal },
];

export function Sidebar() {
  const [location] = useLocation();

  return (
    <aside className="fixed left-0 top-0 h-screen w-64 bg-card/50 backdrop-blur-xl border-r border-border flex flex-col z-50">
      <div className="p-6 border-b border-border/50 flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl bg-primary/20 flex items-center justify-center text-primary">
          <Bot className="w-6 h-6" />
        </div>
        <div>
          <h1 className="font-bold text-lg leading-tight tracking-tight">NetBot</h1>
          <p className="text-xs text-muted-foreground font-mono">v2.1.0-beta</p>
        </div>
      </div>

      <nav className="flex-1 p-4 space-y-2">
        <div className="text-xs font-semibold text-muted-foreground/50 uppercase tracking-wider mb-4 px-2">
          Platform
        </div>
        
        {NAV_ITEMS.map((item) => {
          const isActive = location === item.href;
          return (
            <Link key={item.href} href={item.href}>
              <div
                className={cn(
                  "flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-200 group cursor-pointer",
                  isActive 
                    ? "bg-primary text-primary-foreground shadow-lg shadow-primary/25 font-medium" 
                    : "text-muted-foreground hover:text-foreground hover:bg-white/5"
                )}
              >
                <item.icon className={cn("w-5 h-5", isActive ? "text-primary-foreground" : "text-muted-foreground group-hover:text-foreground")} />
                {item.label}
              </div>
            </Link>
          );
        })}

        <div className="mt-8 text-xs font-semibold text-muted-foreground/50 uppercase tracking-wider mb-4 px-2">
          System
        </div>

        <button className="w-full flex items-center gap-3 px-4 py-3 rounded-xl text-muted-foreground hover:text-foreground hover:bg-white/5 transition-all duration-200 text-left">
          <Activity className="w-5 h-5" />
          System Status
        </button>
        <button className="w-full flex items-center gap-3 px-4 py-3 rounded-xl text-muted-foreground hover:text-foreground hover:bg-white/5 transition-all duration-200 text-left">
          <Settings className="w-5 h-5" />
          Configuration
        </button>
      </nav>

      <div className="p-4 border-t border-border/50 bg-black/20">
        <div className="flex items-center gap-3">
          <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse shadow-[0_0_10px_rgb(34,197,94)]" />
          <span className="text-xs font-mono text-green-500">SYSTEM OPERATIONAL</span>
        </div>
      </div>
    </aside>
  );
}
