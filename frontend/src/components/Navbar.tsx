"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { 
  BarChart3, 
  UploadCloud, 
  GitMerge, 
  Layers, 
  Database, 
  Hexagon
} from "lucide-react";

export default function Navbar() {
  const pathname = usePathname();

  const navItems = [
    { href: "/", label: "Analytics", icon: BarChart3 },
    { href: "/ingestion", label: "Ingestion", icon: UploadCloud },
    { href: "/review", label: "Review Queue", icon: GitMerge },
    { href: "/crosswalk", label: "Crosswalk", icon: Layers },
    { href: "/materials", label: "Catalog", icon: Database },
  ];

  return (
    <header className="sticky top-0 z-50 w-full glass-surface border-b border-white/[0.08] transition-all">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-14">
          {/* Brand Logo & Minimal Tag */}
          <Link href="/" className="flex items-center space-x-2.5 group apple-press-subtle">
            <div className="h-8 w-8 rounded-lg bg-zinc-900 border border-white/10 flex items-center justify-center text-white transition-colors group-hover:border-white/20">
              <Hexagon className="h-4 w-4 text-zinc-100" />
            </div>
            <div className="flex items-baseline space-x-2">
              <span className="font-semibold tracking-tight text-sm text-white">
                UniMM
              </span>
              <span className="text-[11px] text-zinc-500 font-normal hidden sm:inline">
                National Material Master
              </span>
            </div>
          </Link>

          {/* Apple Segmented Pill Navigation */}
          <nav className="flex items-center p-0.5 bg-zinc-900/90 rounded-full border border-white/[0.08] backdrop-blur-md">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = pathname === item.href;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-full text-xs font-medium transition-all duration-150 apple-press ${
                    isActive
                      ? "bg-white text-black shadow-sm font-semibold"
                      : "text-zinc-400 hover:text-zinc-100 hover:bg-white/[0.04]"
                  }`}
                >
                  <Icon className={`h-3.5 w-3.5 ${isActive ? "text-black" : "text-zinc-400"}`} />
                  <span>{item.label}</span>
                </Link>
              );
            })}
          </nav>

          {/* Minimalist Multi-CPSE Status Pill */}
          <div className="flex items-center">
            <div className="flex items-center space-x-2 px-3 py-1 bg-zinc-900/80 rounded-full border border-white/[0.08] text-[11px] text-zinc-300">
              <div className="flex items-center space-x-1">
                <span className="h-1.5 w-1.5 rounded-full bg-zinc-400"></span>
                <span className="font-medium text-zinc-300">CPCL</span>
              </div>
              <span className="text-zinc-600">/</span>
              <div className="flex items-center space-x-1">
                <span className="h-1.5 w-1.5 rounded-full bg-zinc-400"></span>
                <span className="font-medium text-zinc-300">IOCL</span>
              </div>
              <span className="text-zinc-600">/</span>
              <div className="flex items-center space-x-1">
                <span className="h-1.5 w-1.5 rounded-full bg-zinc-400"></span>
                <span className="font-medium text-zinc-300">BPCL</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </header>
  );
}
