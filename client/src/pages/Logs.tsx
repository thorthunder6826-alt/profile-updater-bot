import { Sidebar } from "@/components/Sidebar";
import { Header } from "@/components/Header";
import { useLogs } from "@/hooks/use-api";
import { format } from "date-fns";
import { Terminal, Filter, Download, AlertCircle, Info, CheckCircle2 } from "lucide-react";
import { cn } from "@/lib/utils";

export default function LogsPage() {
  const { data: logs = [], isLoading } = useLogs();

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'success': return <CheckCircle2 className="w-4 h-4 text-green-500" />;
      case 'failed': return <AlertCircle className="w-4 h-4 text-red-500" />;
      default: return <Info className="w-4 h-4 text-blue-500" />;
    }
  };

  return (
    <div className="min-h-screen bg-background text-foreground flex">
      <Sidebar />
      <main className="flex-1 ml-64 flex flex-col min-w-0">
        <Header title="System Logs" />

        <div className="p-8 h-[calc(100vh-80px)] flex flex-col">
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-4">
              <div className="p-3 bg-primary/10 rounded-xl text-primary">
                <Terminal className="w-6 h-6" />
              </div>
              <div>
                <h3 className="font-bold text-lg">Activity Log</h3>
                <p className="text-sm text-muted-foreground">Monitor bot actions and errors in real-time.</p>
              </div>
            </div>

            <div className="flex gap-3">
              <button className="flex items-center gap-2 px-4 py-2 rounded-lg border border-border bg-card hover:bg-white/5 text-sm font-medium transition-colors">
                <Filter className="w-4 h-4" />
                Filter
              </button>
              <button className="flex items-center gap-2 px-4 py-2 rounded-lg border border-border bg-card hover:bg-white/5 text-sm font-medium transition-colors">
                <Download className="w-4 h-4" />
                Export
              </button>
            </div>
          </div>

          <div className="flex-1 glass-panel rounded-2xl border border-white/5 overflow-hidden flex flex-col">
            <div className="px-6 py-4 border-b border-white/5 bg-black/20 flex items-center justify-between">
              <div className="flex gap-2">
                <span className="w-3 h-3 rounded-full bg-red-500/20 border border-red-500/50" />
                <span className="w-3 h-3 rounded-full bg-yellow-500/20 border border-yellow-500/50" />
                <span className="w-3 h-3 rounded-full bg-green-500/20 border border-green-500/50" />
              </div>
              <span className="text-xs font-mono text-muted-foreground">tail -f system.log</span>
            </div>

            <div className="flex-1 overflow-y-auto custom-scrollbar p-4 font-mono text-sm space-y-1">
              {isLoading ? (
                <div className="text-muted-foreground p-4">Loading logs...</div>
              ) : (
                logs.map((log) => (
                  <div key={log.id} className="flex items-start gap-4 p-2 hover:bg-white/5 rounded transition-colors group">
                    <span className="text-muted-foreground/50 shrink-0 w-32">
                      {log.createdAt ? format(new Date(log.createdAt), 'yyyy-MM-dd HH:mm:ss') : '-'}
                    </span>
                    
                    <div className="flex items-center gap-2 w-24 shrink-0">
                      {getStatusIcon(log.status)}
                      <span className={cn(
                        "uppercase text-xs font-bold",
                        log.status === 'success' ? "text-green-500" : 
                        log.status === 'failed' ? "text-red-500" : "text-blue-500"
                      )}>
                        {log.status}
                      </span>
                    </div>

                    <div className="flex-1 text-foreground/90 break-all">
                      <span className="text-primary font-semibold mr-2">[{log.action}]</span>
                      {log.details}
                    </div>

                    <div className="text-xs text-muted-foreground/30 opacity-0 group-hover:opacity-100 transition-opacity">
                      ID: {log.telegramId || 'SYSTEM'}
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
