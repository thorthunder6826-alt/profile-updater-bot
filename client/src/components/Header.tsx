import { Bell, Search, UserCircle } from "lucide-react";

export function Header({ title }: { title: string }) {
  return (
    <header className="h-20 border-b border-border/50 backdrop-blur-md bg-background/50 flex items-center justify-between px-8 sticky top-0 z-40">
      <div>
        <h2 className="text-2xl font-bold tracking-tight text-foreground">{title}</h2>
      </div>

      <div className="flex items-center gap-4">
        <div className="relative group">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground group-focus-within:text-primary transition-colors" />
          <input 
            type="text" 
            placeholder="Search..." 
            className="pl-10 pr-4 py-2 rounded-xl bg-card border border-border text-sm w-64 focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary/50 transition-all placeholder:text-muted-foreground/50"
          />
        </div>

        <button className="relative p-2.5 rounded-xl hover:bg-white/5 text-muted-foreground hover:text-foreground transition-colors">
          <Bell className="w-5 h-5" />
          <span className="absolute top-2.5 right-2.5 w-2 h-2 bg-primary rounded-full ring-2 ring-background animate-pulse" />
        </button>
        
        <div className="h-8 w-[1px] bg-border mx-2" />
        
        <button className="flex items-center gap-3 p-1.5 pr-4 rounded-xl hover:bg-white/5 border border-transparent hover:border-white/5 transition-all group">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-primary to-purple-500 flex items-center justify-center text-white shadow-lg shadow-primary/20 group-hover:shadow-primary/40 transition-shadow">
            <span className="font-bold text-xs">AD</span>
          </div>
          <div className="text-left hidden md:block">
            <p className="text-sm font-medium text-foreground group-hover:text-primary transition-colors">Admin User</p>
            <p className="text-xs text-muted-foreground">Super Admin</p>
          </div>
        </button>
      </div>
    </header>
  );
}
