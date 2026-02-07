import { Sidebar } from "@/components/Sidebar";
import { Header } from "@/components/Header";
import { useBotStatus } from "@/hooks/use-api";
import { Bot, Activity, Wifi, WifiOff, Clock } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

function formatUptime(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = Math.floor(seconds % 60);
  if (h > 0) return `${h}h ${m}m ${s}s`;
  if (m > 0) return `${m}m ${s}s`;
  return `${s}s`;
}

export default function Dashboard() {
  const { data: status, isLoading } = useBotStatus();

  return (
    <div className="min-h-screen bg-background text-foreground flex">
      <Sidebar />
      <main className="flex-1 ml-64 flex flex-col min-w-0">
        <Header title="Dashboard" />

        <div className="p-8 space-y-8 overflow-y-auto max-h-[calc(100vh-80px)]">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <Card data-testid="card-bot-status">
              <CardHeader className="flex flex-row items-center justify-between gap-2 space-y-0 pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">Bot Status</CardTitle>
                <Bot className="w-5 h-5 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                {isLoading ? (
                  <p className="text-muted-foreground text-sm">Loading...</p>
                ) : (
                  <div className="flex items-center gap-2">
                    {status?.online ? (
                      <>
                        <Wifi className="w-5 h-5 text-green-500" />
                        <span className="text-2xl font-bold" data-testid="text-status">Online</span>
                      </>
                    ) : (
                      <>
                        <WifiOff className="w-5 h-5 text-red-500" />
                        <span className="text-2xl font-bold" data-testid="text-status">Offline</span>
                      </>
                    )}
                  </div>
                )}
              </CardContent>
            </Card>

            <Card data-testid="card-uptime">
              <CardHeader className="flex flex-row items-center justify-between gap-2 space-y-0 pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">Uptime</CardTitle>
                <Clock className="w-5 h-5 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <p className="text-2xl font-bold" data-testid="text-uptime">
                  {status ? formatUptime(status.uptime) : "--"}
                </p>
              </CardContent>
            </Card>

            <Card data-testid="card-activity">
              <CardHeader className="flex flex-row items-center justify-between gap-2 space-y-0 pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">Activity</CardTitle>
                <Activity className="w-5 h-5 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <p className="text-2xl font-bold" data-testid="text-activity">
                  {status?.online ? "Running" : "Stopped"}
                </p>
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader>
              <CardTitle>Bot Commands Reference</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                <div className="space-y-3">
                  <h4 className="font-semibold text-muted-foreground">Session</h4>
                  <div className="space-y-2">
                    <div className="font-mono bg-muted p-2 rounded-md" data-testid="text-cmd-login">/login &lt;cookie&gt;</div>
                    <div className="font-mono bg-muted p-2 rounded-md" data-testid="text-cmd-loginemail">/loginemail &lt;email&gt; &lt;password&gt;</div>
                    <div className="font-mono bg-muted p-2 rounded-md" data-testid="text-cmd-logout">/logout</div>
                    <div className="font-mono bg-muted p-2 rounded-md" data-testid="text-cmd-profiles">/profiles</div>
                  </div>
                </div>
                <div className="space-y-3">
                  <h4 className="font-semibold text-muted-foreground">Profile Management</h4>
                  <div className="space-y-2">
                    <div className="font-mono bg-muted p-2 rounded-md" data-testid="text-cmd-updateall">/updateallprofiles &lt;names...&gt; &lt;password&gt;</div>
                    <div className="font-mono bg-muted p-2 rounded-md" data-testid="text-cmd-updatepins">/updateallpins &lt;pins...&gt; &lt;password&gt;</div>
                    <div className="font-mono bg-muted p-2 rounded-md" data-testid="text-cmd-addprofile">/addprofile &lt;name&gt;</div>
                    <div className="font-mono bg-muted p-2 rounded-md" data-testid="text-cmd-delete">/deleteprofile &lt;guid&gt;</div>
                  </div>
                </div>
                <div className="space-y-3">
                  <h4 className="font-semibold text-muted-foreground">Admin</h4>
                  <div className="space-y-2">
                    <div className="font-mono bg-muted p-2 rounded-md" data-testid="text-cmd-adduser">/adduser &lt;telegram_id&gt;</div>
                    <div className="font-mono bg-muted p-2 rounded-md" data-testid="text-cmd-removeuser">/removeuser &lt;telegram_id&gt;</div>
                    <div className="font-mono bg-muted p-2 rounded-md" data-testid="text-cmd-listusers">/listusers</div>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </main>
    </div>
  );
}
