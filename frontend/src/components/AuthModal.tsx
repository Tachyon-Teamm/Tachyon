"use client";

import { useState } from "react";
import { X, ShieldCheck, UserCheck, Key, Lock, ArrowRight, CheckCircle2 } from "lucide-react";
import { api } from "@/lib/api";

interface AuthModalProps {
  isOpen: boolean;
  onClose: () => void;
  onLoginSuccess?: (user: { username: string; role: string; cpse_code?: string }) => void;
}

const SEEDED_PERSONAS = [
  {
    username: "admin",
    role: "System Admin",
    org: "National Master Authority",
    badge: "Superuser",
    desc: "Full administrative, minting, dispute override & audit authority",
  },
  {
    username: "steward",
    role: "Data Steward",
    org: "IOCL",
    badge: "Steward",
    desc: "Batch ingestion, column schema mapping & catalog curation",
  },
  {
    username: "reviewer",
    role: "Domain Reviewer",
    org: "CPCL",
    badge: "Reviewer",
    desc: "Technical review queue approval, duplicate merging & dispute filing",
  },
  {
    username: "viewer",
    role: "Catalog Viewer",
    org: "BPCL",
    badge: "Read-Only",
    desc: "Crosswalk reverse lookups, catalog export & inventory analytics",
  },
];

export default function AuthModal({ isOpen, onClose, onLoginSuccess }: AuthModalProps) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successUser, setSuccessUser] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleLogin = async (loginUser: string, loginPass: string) => {
    setIsLoading(true);
    setError(null);
    try {
      const res = await api.login(loginUser, loginPass);
      setSuccessUser(res.username);
      if (onLoginSuccess) {
        onLoginSuccess({
          username: res.username,
          role: res.role,
          cpse_code: res.cpse_code,
        });
      }
      setTimeout(() => {
        onClose();
        setSuccessUser(null);
      }, 700);
    } catch (err: any) {
      setError(err.message || "Invalid credentials or backend authentication error");
    } finally {
      setIsLoading(false);
    }
  };

  const onSubmitCustom = (e: React.FormEvent) => {
    e.preventDefault();
    if (!username || !password) {
      setError("Please enter both username and password");
      return;
    }
    handleLogin(username, password);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 dark:bg-black/80 backdrop-blur-md animate-in fade-in duration-200">
      <div className="relative w-full max-w-lg overflow-hidden rounded-2xl bg-white dark:bg-zinc-950 border border-zinc-200 dark:border-white/10 shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-zinc-100 dark:border-white/[0.08] bg-zinc-50/80 dark:bg-zinc-900/50">
          <div className="flex items-center space-x-2.5">
            <div className="h-8 w-8 rounded-lg bg-zinc-100 dark:bg-zinc-800 border border-zinc-200 dark:border-white/10 flex items-center justify-center text-zinc-900 dark:text-zinc-100">
              <ShieldCheck className="h-4 w-4" />
            </div>
            <div>
              <h2 className="text-sm font-semibold text-zinc-900 dark:text-white tracking-tight">UniMM Identity & RBAC</h2>
              <p className="text-[11px] text-zinc-500 dark:text-zinc-400">Authenticate for role-based catalog governance</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg text-zinc-500 hover:text-zinc-900 hover:bg-zinc-100 dark:text-zinc-400 dark:hover:text-zinc-100 dark:hover:bg-white/[0.06] transition-colors"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-5">
          {error && (
            <div className="p-3 text-xs rounded-xl bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-500/30 text-red-700 dark:text-red-300">
              {error}
            </div>
          )}

          {successUser && (
            <div className="flex items-center space-x-2 p-3 text-xs rounded-xl bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-500/30 text-emerald-800 dark:text-emerald-300">
              <CheckCircle2 className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
              <span>Signed in as <strong className="font-semibold">{successUser}</strong>. Updating session...</span>
            </div>
          )}

          {/* Quick Demo Personas */}
          <div>
            <label className="text-[11px] uppercase tracking-wider font-semibold text-zinc-500 dark:text-zinc-400 block mb-2">
              Quick One-Click Personas (Pre-Seeded)
            </label>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {SEEDED_PERSONAS.map((p) => (
                <button
                  key={p.username}
                  type="button"
                  disabled={isLoading}
                  onClick={() => handleLogin(p.username, "password")}
                  className="text-left p-3 rounded-xl bg-zinc-50 dark:bg-zinc-900/60 border border-zinc-200 dark:border-white/[0.06] hover:border-zinc-300 dark:hover:border-white/20 hover:bg-zinc-100/80 dark:hover:bg-zinc-800/50 transition-all group relative overflow-hidden"
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs font-semibold text-zinc-900 group-hover:text-black dark:text-zinc-100 dark:group-hover:text-white flex items-center gap-1.5">
                      <UserCheck className="h-3.5 w-3.5 text-zinc-500 group-hover:text-zinc-900 dark:text-zinc-400 dark:group-hover:text-white" />
                      {p.username}
                    </span>
                    <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-zinc-200/70 text-zinc-700 dark:bg-white/[0.08] dark:text-zinc-300 font-mono">
                      {p.badge}
                    </span>
                  </div>
                  <p className="text-[10px] text-zinc-500 dark:text-zinc-400 line-clamp-1">{p.role} · {p.org}</p>
                </button>
              ))}
            </div>
          </div>

          <div className="relative flex items-center justify-center">
            <div className="border-t border-zinc-200 dark:border-white/[0.08] w-full"></div>
            <span className="bg-white dark:bg-zinc-950 px-3 text-[10px] uppercase font-mono tracking-widest text-zinc-400 dark:text-zinc-500">
              Or Custom Credentials
            </span>
          </div>

          {/* Custom Login Form */}
          <form onSubmit={onSubmitCustom} className="space-y-3">
            <div>
              <label className="text-[11px] font-medium text-zinc-700 dark:text-zinc-300 block mb-1">Username</label>
              <div className="relative">
                <input
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="e.g. admin, steward, or custom username"
                  className="w-full px-3 py-2 pl-9 rounded-xl bg-zinc-50 dark:bg-zinc-900/80 border border-zinc-200 dark:border-white/10 text-xs text-zinc-900 dark:text-white placeholder-zinc-400 dark:placeholder-zinc-500 focus:outline-none focus:border-zinc-400 dark:focus:border-white/30 transition-colors"
                />
                <Key className="absolute left-3 top-2.5 h-3.5 w-3.5 text-zinc-400 dark:text-zinc-500" />
              </div>
            </div>

            <div>
              <label className="text-[11px] font-medium text-zinc-700 dark:text-zinc-300 block mb-1">Password</label>
              <div className="relative">
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Default seed password: password"
                  className="w-full px-3 py-2 pl-9 rounded-xl bg-zinc-50 dark:bg-zinc-900/80 border border-zinc-200 dark:border-white/10 text-xs text-zinc-900 dark:text-white placeholder-zinc-400 dark:placeholder-zinc-500 focus:outline-none focus:border-zinc-400 dark:focus:border-white/30 transition-colors"
                />
                <Lock className="absolute left-3 top-2.5 h-3.5 w-3.5 text-zinc-400 dark:text-zinc-500" />
              </div>
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="w-full mt-2 flex items-center justify-center space-x-2 px-4 py-2.5 rounded-xl bg-zinc-900 text-white hover:bg-zinc-800 dark:bg-white dark:text-black dark:hover:bg-zinc-200 font-semibold text-xs transition-colors disabled:opacity-50 shadow-sm"
            >
              <span>{isLoading ? "Authenticating..." : "Sign In"}</span>
              <ArrowRight className="h-3.5 w-3.5" />
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
