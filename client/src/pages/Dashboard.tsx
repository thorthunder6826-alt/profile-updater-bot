import { Sidebar } from "@/components/Sidebar";
import { Header } from "@/components/Header";
import { StatsCard } from "@/components/StatsCard";
import { useUsers, useLogs } from "@/hooks/use-api";
import { Users, Activity, CheckCircle2, XCircle, Clock } from "lucide-react";
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, AreaChart, Area } from "recharts";
import { format } from "date-fns";
import { motion } from "framer-motion";

export default function Dashboard() {
  const { data: users = [] } = useUsers();
  const { data: logs = [] } = useLogs();

  const totalUsers = users.length;
  const activeUsers = users.filter(u => u.isLoggedIn).length;
  const successLogs = logs.filter(l => l.status === "success").length;
  const failedLogs = logs.filter(l => l.status === "failed").length;

  // Mock data for the chart
  const chartData = [
    { name: 'Mon', updates: 40, errors: 24 },
    { name: 'Tue', updates: 30, errors: 13 },
    { name: 'Wed', updates: 20, errors: 98 },
    { name: 'Thu', updates: 27, errors: 39 },
    { name: 'Fri', updates: 18, errors: 48 },
    { name: 'Sat', updates: 23, errors: 38 },
    { name: 'Sun', updates: 34, errors: 43 },
  ];

  return (
    <div className="min-h-screen bg-background text-foreground flex">
      <Sidebar />
      <main className="flex-1 ml-64 flex flex-col min-w-0">
        <Header title="Dashboard Overview" />
        
        <div className="p-8 space-y-8 overflow-y-auto max-h-[calc(100vh-80px)] custom-scrollbar">
          {/* Stats Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.0 }}>
              <StatsCard 
                title="Total Users" 
                value={totalUsers} 
                icon={<Users className="w-6 h-6" />} 
                trend={{ value: 12, isPositive: true }}
              />
            </motion.div>
            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}>
              <StatsCard 
                title="Active Sessions" 
                value={activeUsers} 
                icon={<Activity className="w-6 h-6" />} 
                trend={{ value: 5, isPositive: true }}
                className="border-primary/20"
              />
            </motion.div>
            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}>
              <StatsCard 
                title="Successful Updates" 
                value={successLogs} 
                icon={<CheckCircle2 className="w-6 h-6" />} 
                trend={{ value: 24, isPositive: true }}
              />
            </motion.div>
            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }}>
              <StatsCard 
                title="Failed Attempts" 
                value={failedLogs} 
                icon={<XCircle className="w-6 h-6" />} 
                trend={{ value: 2, isPositive: false }}
              />
            </motion.div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Chart */}
            <motion.div 
              initial={{ opacity: 0, scale: 0.95 }} 
              animate={{ opacity: 1, scale: 1 }} 
              transition={{ delay: 0.4 }}
              className="lg:col-span-2 glass-panel rounded-2xl p-6 border-white/5"
            >
              <div className="flex items-center justify-between mb-6">
                <h3 className="text-lg font-bold">Bot Activity</h3>
                <div className="flex items-center gap-2 text-sm bg-black/20 p-1 rounded-lg">
                  <button className="px-3 py-1 bg-primary/20 text-primary rounded-md font-medium">Weekly</button>
                  <button className="px-3 py-1 text-muted-foreground hover:text-foreground">Monthly</button>
                </div>
              </div>
              <div className="h-[300px] w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={chartData}>
                    <defs>
                      <linearGradient id="colorUpdates" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="hsl(var(--primary))" stopOpacity={0.3}/>
                        <stop offset="95%" stopColor="hsl(var(--primary))" stopOpacity={0}/>
                      </linearGradient>
                    </defs>
                    <XAxis 
                      dataKey="name" 
                      stroke="#444" 
                      fontSize={12} 
                      tickLine={false} 
                      axisLine={false} 
                    />
                    <YAxis 
                      stroke="#444" 
                      fontSize={12} 
                      tickLine={false} 
                      axisLine={false} 
                      tickFormatter={(value) => `${value}`}
                    />
                    <Tooltip 
                      contentStyle={{ backgroundColor: '#111', borderColor: '#333', borderRadius: '8px' }}
                      itemStyle={{ color: '#fff' }}
                    />
                    <Area 
                      type="monotone" 
                      dataKey="updates" 
                      stroke="hsl(var(--primary))" 
                      strokeWidth={3}
                      fillOpacity={1} 
                      fill="url(#colorUpdates)" 
                    />
                    <Line 
                      type="monotone" 
                      dataKey="errors" 
                      stroke="#ef4444" 
                      strokeWidth={2} 
                      strokeDasharray="5 5" 
                      dot={false}
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </motion.div>

            {/* Recent Logs List */}
            <motion.div 
              initial={{ opacity: 0, x: 20 }} 
              animate={{ opacity: 1, x: 0 }} 
              transition={{ delay: 0.5 }}
              className="glass-panel rounded-2xl p-6 border-white/5 flex flex-col"
            >
              <h3 className="text-lg font-bold mb-4">Recent Logs</h3>
              <div className="space-y-4 overflow-y-auto pr-2 flex-1 custom-scrollbar">
                {logs.slice(0, 6).map((log) => (
                  <div key={log.id} className="flex gap-4 p-3 rounded-xl bg-white/5 hover:bg-white/10 transition-colors border border-white/5">
                    <div className={cn(
                      "w-10 h-10 rounded-full flex items-center justify-center shrink-0",
                      log.status === 'success' ? "bg-green-500/20 text-green-500" : "bg-red-500/20 text-red-500"
                    )}>
                      {log.status === 'success' ? <CheckCircle2 className="w-5 h-5" /> : <XCircle className="w-5 h-5" />}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between mb-1">
                        <p className="text-sm font-semibold truncate">{log.action}</p>
                        <span className="text-[10px] text-muted-foreground font-mono bg-black/40 px-1.5 py-0.5 rounded">
                          {format(new Date(log.createdAt || ""), 'HH:mm')}
                        </span>
                      </div>
                      <p className="text-xs text-muted-foreground truncate">{log.details}</p>
                    </div>
                  </div>
                ))}
              </div>
              <button className="mt-4 w-full py-2.5 text-sm font-medium text-muted-foreground hover:text-primary transition-colors border-t border-border/50">
                View All Logs
              </button>
            </motion.div>
          </div>
        </div>
      </main>
    </div>
  );
}
