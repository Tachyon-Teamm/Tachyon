"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { 
  BarChart3, 
  UploadCloud, 
  GitMerge, 
  Layers, 
  Database, 
  Hexagon,
  LogOut,
  Key,
  Search
} from "lucide-react";
import { api } from "@/lib/api";
import AuthModal from "./AuthModal";
import ThemeToggle from "./ThemeToggle";
import SpotlightModal from "./SpotlightModal";

export default function Navbar() {
  const pathname = usePathname();
  const [isAuthOpen, setIsAuthOpen] = useState(false);
  const [isSpotlightOpen, setIsSpotlightOpen] = useState(false);
  const [currentUser, setCurrentUser] = useState<{ username: string; role: string; cpse_code?: string } | null>(null);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setIsSpotlightOpen((prev) => !prev);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  useEffect(() => {
    const user = api.getStoredUser();
    if (user) {
      setCurrentUser(user);
    }
  }, []);

  const handleLogout = () => {
    api.logout();
    setCurrentUser(null);
  };

  const navItems = [
    { href: "/", label: "Overview", icon: BarChart3 },
    { href: "/ingestion", label: "Import", icon: UploadCloud },
    { href: "/review", label: "Review", icon: GitMerge },
    { href: "/materials", label: "Directory", icon: Database },
  ];

  return (
    <>
      <header className="sticky top-0 z-40 w-full glass-surface border-b border-zinc-200/80 dark:border-white/[0.08] transition-colors">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-14">
            {/* Brand Logo & Minimal Tag */}
            <Link href="/" className="flex items-center space-x-2.5 group apple-press-subtle">
              <div className="h-8 w-8 rounded-lg bg-zinc-100 dark:bg-zinc-900 border border-zinc-300/80 dark:border-white/10 flex items-center justify-center text-zinc-900 dark:text-white transition-colors group-hover:border-zinc-400 dark:group-hover:border-white/20">
                <Hexagon className="h-4 w-4 text-zinc-900 dark:text-zinc-100" />
              </div>
              <div className="flex items-baseline space-x-2">
                <span className="font-semibold tracking-tight text-sm text-zinc-900 dark:text-white">
                  UniMM
                </span>
                <span className="text-[11px] text-zinc-500 dark:text-zinc-400 font-normal hidden sm:inline">
                  National Material Master
                </span>
              </div>
            </Link>

            {/* Apple Segmented Pill Navigation */}
            <nav className="flex items-center p-0.5 bg-zinc-100/90 dark:bg-zinc-900/90 rounded-lg border border-zinc-200 dark:border-zinc-800 backdrop-blur-md">
              {navItems.map((item) => {
                const Icon = item.icon;
                const isActive = item.href === "/materials"
                  ? (pathname === "/materials" || pathname === "/crosswalk")
                  : pathname === item.href;
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={`flex items-center space-x-1.5 px-3.5 py-1.5 rounded-md text-xs font-medium transition-all duration-150 apple-press ${
                      isActive
                        ? "bg-white dark:bg-zinc-100 text-zinc-950 dark:text-zinc-950 shadow-sm font-semibold"
                        : "text-zinc-600 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-zinc-200 hover:bg-zinc-200/60 dark:hover:bg-zinc-800/60"
                    }`}
                  >
                    <Icon className={`h-3.5 w-3.5 ${isActive ? "text-zinc-950" : "text-zinc-500 dark:text-zinc-400"}`} />
                    <span>{item.label}</span>
                  </Link>
                );
              })}
            </nav>

            {/* Right Side: Spotlight Trigger, Multi-Sector CPSE Status, Theme Toggle & Auth */}
            <div className="flex items-center space-x-2.5">
              {/* Spotlight Global Trigger */}
              <button
                onClick={() => setIsSpotlightOpen(true)}
                className="flex items-center space-x-2 h-8 px-2.5 rounded-lg bg-zinc-100/90 hover:bg-zinc-200/90 dark:bg-zinc-900/90 dark:hover:bg-zinc-800/90 border border-zinc-200 dark:border-zinc-800 text-xs text-zinc-500 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-zinc-100 transition apple-press"
                title="Spotlight Search (⌘K)"
              >
                <Search className="h-3.5 w-3.5" />
                <span className="hidden md:inline font-sans text-xs">Spotlight</span>
                <kbd className="hidden sm:inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-mono font-semibold bg-zinc-200 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-300">
                  ⌘K
                </kbd>
              </button>

              {/* Multi-Sector CPSE Scope Pill */}
              <div className="hidden lg:flex items-center space-x-1.5 px-2.5 py-1 bg-zinc-100/80 dark:bg-zinc-900/80 rounded-md border border-zinc-200 dark:border-zinc-800 text-xs text-zinc-600 dark:text-zinc-400 font-mono">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 dark:bg-emerald-400/80"></span>
                <span className="font-medium text-zinc-800 dark:text-zinc-300">8 CPSEs</span>
                <span className="text-zinc-400 dark:text-zinc-600">·</span>
                <span className="text-zinc-500 dark:text-zinc-400 text-[11px]">5 Sectors</span>
              </div>

              {/* Theme Toggle Button */}
              <ThemeToggle />

              {/* User Authentication Pill / Button */}
              {currentUser ? (
                <div className="flex items-center space-x-1.5 pl-2.5 pr-1.5 py-1 bg-zinc-100/90 dark:bg-zinc-900/90 rounded-md border border-zinc-200 dark:border-zinc-800 text-xs text-zinc-800 dark:text-zinc-200">
                  <div className="flex items-center space-x-1.5">
                    <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 dark:bg-emerald-400/80"></span>
                    <span className="font-medium text-zinc-900 dark:text-zinc-200">{currentUser.username}</span>
                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-zinc-200 dark:bg-zinc-800 text-zinc-700 dark:text-zinc-400 font-mono">
                      {currentUser.role}
                    </span>
                  </div>
                  <button
                    onClick={handleLogout}
                    title="Sign Out"
                    className="p-1 rounded text-zinc-500 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-white hover:bg-zinc-200 dark:hover:bg-zinc-800 transition-colors"
                  >
                    <LogOut className="h-3 w-3" />
                  </button>
                </div>
              ) : (
                <button
                  onClick={() => setIsAuthOpen(true)}
                  className="flex items-center space-x-1.5 px-3 py-1 bg-zinc-100 hover:bg-zinc-200 dark:bg-zinc-900 dark:hover:bg-zinc-800 border border-zinc-200 dark:border-zinc-800 rounded-md text-xs font-medium text-zinc-800 hover:text-zinc-950 dark:text-zinc-200 dark:hover:text-white transition-all apple-press"
                >
                  <Key className="h-3 w-3 text-zinc-500 dark:text-zinc-400" />
                  <span>Sign In</span>
                </button>
              )}
            </div>
          </div>
        </div>
      </header>

      <AuthModal
        isOpen={isAuthOpen}
        onClose={() => setIsAuthOpen(false)}
        onLoginSuccess={(user) => setCurrentUser(user)}
      />

      <SpotlightModal
        isOpen={isSpotlightOpen}
        onClose={() => setIsSpotlightOpen(false)}
      />
    </>
  );
}
