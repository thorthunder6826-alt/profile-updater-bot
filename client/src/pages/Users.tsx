import { Sidebar } from "@/components/Sidebar";
import { Header } from "@/components/Header";
import { useUsers, useDeleteUser, useCreateUser } from "@/hooks/use-api";
import { Plus, MoreHorizontal, Trash2, Mail, ExternalLink, ShieldAlert, MonitorPlay } from "lucide-react";
import { useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { format } from "date-fns";
import { motion, AnimatePresence } from "framer-motion";

export default function UsersPage() {
  const { data: users = [], isLoading } = useUsers();
  const deleteMutation = useDeleteUser();
  const createMutation = useCreateUser();
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [isDeleteOpen, setIsDeleteOpen] = useState<number | null>(null);

  // Form state
  const [formData, setFormData] = useState({
    telegramId: "",
    username: "",
    netflixEmail: "",
  });

  const handleCreate = async () => {
    try {
      await createMutation.mutateAsync(formData as any);
      setIsCreateOpen(false);
      setFormData({ telegramId: "", username: "", netflixEmail: "" });
    } catch (e) {
      console.error(e);
    }
  };

  const handleDelete = async () => {
    if (isDeleteOpen) {
      await deleteMutation.mutateAsync(isDeleteOpen);
      setIsDeleteOpen(null);
    }
  };

  return (
    <div className="min-h-screen bg-background text-foreground flex">
      <Sidebar />
      <main className="flex-1 ml-64 flex flex-col min-w-0">
        <Header title="User Management" />

        <div className="p-8">
          <div className="flex justify-between items-center mb-8">
            <p className="text-muted-foreground">Manage Telegram users connected to the bot.</p>
            <Dialog open={isCreateOpen} onOpenChange={setIsCreateOpen}>
              <DialogTrigger asChild>
                <button className="flex items-center gap-2 bg-primary text-primary-foreground px-6 py-2.5 rounded-xl font-medium shadow-lg shadow-primary/25 hover:shadow-primary/40 hover:-translate-y-0.5 transition-all duration-200">
                  <Plus className="w-5 h-5" />
                  Add User
                </button>
              </DialogTrigger>
              <DialogContent className="bg-card border-border sm:max-w-md">
                <DialogHeader>
                  <DialogTitle>Add New User</DialogTitle>
                  <DialogDescription>
                    Manually add a Telegram user to the database.
                  </DialogDescription>
                </DialogHeader>
                <div className="space-y-4 py-4">
                  <div className="space-y-2">
                    <label className="text-sm font-medium">Telegram ID</label>
                    <input 
                      value={formData.telegramId}
                      onChange={(e) => setFormData({ ...formData, telegramId: e.target.value })}
                      className="w-full bg-background border border-input rounded-lg px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
                      placeholder="e.g. 123456789"
                    />
                  </div>
                  <div className="space-y-2">
                    <label className="text-sm font-medium">Username</label>
                    <input 
                      value={formData.username}
                      onChange={(e) => setFormData({ ...formData, username: e.target.value })}
                      className="w-full bg-background border border-input rounded-lg px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
                      placeholder="@username"
                    />
                  </div>
                  <div className="space-y-2">
                    <label className="text-sm font-medium">Netflix Email</label>
                    <input 
                      value={formData.netflixEmail}
                      onChange={(e) => setFormData({ ...formData, netflixEmail: e.target.value })}
                      className="w-full bg-background border border-input rounded-lg px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
                      placeholder="email@example.com"
                    />
                  </div>
                </div>
                <DialogFooter>
                  <button 
                    onClick={handleCreate}
                    disabled={createMutation.isPending}
                    className="bg-primary text-primary-foreground px-4 py-2 rounded-lg text-sm font-medium hover:bg-primary/90 disabled:opacity-50"
                  >
                    {createMutation.isPending ? "Creating..." : "Create User"}
                  </button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
          </div>

          <div className="glass-panel rounded-2xl border border-white/5 overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="bg-white/5 text-muted-foreground font-medium border-b border-white/5">
                  <tr>
                    <th className="px-6 py-4">User</th>
                    <th className="px-6 py-4">Status</th>
                    <th className="px-6 py-4">Netflix Account</th>
                    <th className="px-6 py-4">Last Active</th>
                    <th className="px-6 py-4 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5">
                  {isLoading ? (
                    <tr>
                      <td colSpan={5} className="px-6 py-8 text-center text-muted-foreground">Loading users...</td>
                    </tr>
                  ) : (
                    <AnimatePresence>
                      {users.map((user) => (
                        <motion.tr 
                          key={user.id}
                          initial={{ opacity: 0 }}
                          animate={{ opacity: 1 }}
                          exit={{ opacity: 0 }}
                          className="hover:bg-white/[0.02] transition-colors"
                        >
                          <td className="px-6 py-4">
                            <div className="flex items-center gap-3">
                              <div className="w-10 h-10 rounded-full bg-gradient-to-br from-gray-700 to-gray-900 flex items-center justify-center text-white font-bold border border-white/10">
                                {user.username?.[0]?.toUpperCase() || "U"}
                              </div>
                              <div>
                                <div className="font-semibold text-foreground flex items-center gap-2">
                                  {user.username || "Unknown"}
                                  <a href={`https://t.me/${user.username}`} target="_blank" rel="noreferrer" className="text-muted-foreground hover:text-primary transition-colors">
                                    <ExternalLink className="w-3 h-3" />
                                  </a>
                                </div>
                                <div className="text-xs text-muted-foreground font-mono">{user.telegramId}</div>
                              </div>
                            </div>
                          </td>
                          <td className="px-6 py-4">
                            {user.isLoggedIn ? (
                              <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-green-500/10 text-green-500 border border-green-500/20">
                                <span className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse" />
                                Online
                              </span>
                            ) : (
                              <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-muted text-muted-foreground border border-white/5">
                                Offline
                              </span>
                            )}
                          </td>
                          <td className="px-6 py-4">
                            <div className="flex items-center gap-2 text-muted-foreground">
                              <Mail className="w-4 h-4" />
                              <span className="truncate max-w-[150px]">{user.netflixEmail || "Not linked"}</span>
                            </div>
                          </td>
                          <td className="px-6 py-4 text-muted-foreground">
                            {user.lastActive ? (
                              <div className="flex items-center gap-2">
                                <MonitorPlay className="w-4 h-4" />
                                {format(new Date(user.lastActive), 'MMM d, HH:mm')}
                              </div>
                            ) : (
                              "Never"
                            )}
                          </td>
                          <td className="px-6 py-4 text-right">
                            <div className="flex items-center justify-end gap-2">
                              <button className="p-2 rounded-lg hover:bg-white/5 text-muted-foreground hover:text-foreground transition-colors">
                                <MoreHorizontal className="w-4 h-4" />
                              </button>
                              
                              <Dialog open={isDeleteOpen === user.id} onOpenChange={(open) => !open && setIsDeleteOpen(null)}>
                                <DialogTrigger asChild>
                                  <button 
                                    onClick={() => setIsDeleteOpen(user.id)}
                                    className="p-2 rounded-lg hover:bg-red-500/10 text-muted-foreground hover:text-red-500 transition-colors"
                                  >
                                    <Trash2 className="w-4 h-4" />
                                  </button>
                                </DialogTrigger>
                                <DialogContent className="bg-card border-border">
                                  <DialogHeader>
                                    <DialogTitle>Delete User</DialogTitle>
                                    <DialogDescription>
                                      Are you sure you want to delete <span className="font-bold text-foreground">{user.username}</span>? This action cannot be undone.
                                    </DialogDescription>
                                  </DialogHeader>
                                  <DialogFooter>
                                    <button 
                                      onClick={() => setIsDeleteOpen(null)}
                                      className="px-4 py-2 rounded-lg text-sm font-medium hover:bg-white/5"
                                    >
                                      Cancel
                                    </button>
                                    <button 
                                      onClick={handleDelete}
                                      className="bg-destructive text-destructive-foreground px-4 py-2 rounded-lg text-sm font-medium hover:bg-destructive/90"
                                    >
                                      Delete
                                    </button>
                                  </DialogFooter>
                                </DialogContent>
                              </Dialog>
                            </div>
                          </td>
                        </motion.tr>
                      ))}
                    </AnimatePresence>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
