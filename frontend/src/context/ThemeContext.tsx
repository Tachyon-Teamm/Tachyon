"use client";

import React, { createContext, useContext, useEffect, useState, useCallback } from "react";

export type Theme = "system" | "light" | "dark";
export type ResolvedTheme = "light" | "dark";

interface ThemeContextType {
  theme: Theme;
  resolvedTheme: ResolvedTheme;
  setTheme: (theme: Theme) => void;
  toggleTheme: () => void;
}

const STORAGE_KEY = "unimm_theme";

const safeStorage = {
  getItem: (key: string): string | null => {
    try {
      return typeof window !== "undefined" ? localStorage.getItem(key) : null;
    } catch {
      return null;
    }
  },
  setItem: (key: string, value: string): void => {
    try {
      if (typeof window !== "undefined") {
        localStorage.setItem(key, value);
      }
    } catch {}
  },
};

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

function disableTransitionsTemporarily() {
  if (typeof document === "undefined") return () => {};
  const css = document.createElement("style");
  css.appendChild(
    document.createTextNode(
      "*, *::before, *::after { transition: none !important; animation-duration: 0.001s !important; }"
    )
  );
  document.head.appendChild(css);
  return () => {
    // Force layout recalculation then remove style node
    void window.getComputedStyle(css).opacity;
    document.head.removeChild(css);
  };
}

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [theme, setThemeState] = useState<Theme>("system");
  const [resolvedTheme, setResolvedTheme] = useState<ResolvedTheme>("dark");

  // Read initial stored theme
  useEffect(() => {
    const saved = safeStorage.getItem(STORAGE_KEY) as Theme | null;
    if (saved === "light" || saved === "dark" || saved === "system") {
      setThemeState(saved);
    }
  }, []);

  // Compute resolvedTheme and update DOM class
  const applyTheme = useCallback((targetTheme: Theme) => {
    if (typeof window === "undefined") return;

    const mediaQuery = window.matchMedia("(prefers-color-scheme: dark)");
    const systemDark = mediaQuery.matches;
    const resolved: ResolvedTheme =
      targetTheme === "system" ? (systemDark ? "dark" : "light") : targetTheme;

    setResolvedTheme(resolved);

    const enableTransitions = disableTransitionsTemporarily();
    const root = document.documentElement;

    if (resolved === "dark") {
      root.classList.add("dark");
    } else {
      root.classList.remove("dark");
    }
    root.style.colorScheme = resolved;

    requestAnimationFrame(() => {
      enableTransitions();
    });
  }, []);

  useEffect(() => {
    applyTheme(theme);
  }, [theme, applyTheme]);

  // Listen to OS appearance changes when in "system" mode
  useEffect(() => {
    if (typeof window === "undefined") return;
    const mediaQuery = window.matchMedia("(prefers-color-scheme: dark)");

    const handleChange = () => {
      if (theme === "system") {
        applyTheme("system");
      }
    };

    if (typeof mediaQuery.addEventListener === "function") {
      mediaQuery.addEventListener("change", handleChange);
      return () => mediaQuery.removeEventListener("change", handleChange);
    } else if (typeof (mediaQuery as any).addListener === "function") {
      (mediaQuery as any).addListener(handleChange);
      return () => (mediaQuery as any).removeListener(handleChange);
    }
  }, [theme, applyTheme]);

  // Multi-tab synchronization
  useEffect(() => {
    if (typeof window === "undefined") return;

    const handleStorage = (e: StorageEvent) => {
      if (e.key === STORAGE_KEY && e.newValue) {
        const nextTheme = e.newValue as Theme;
        if (nextTheme === "light" || nextTheme === "dark" || nextTheme === "system") {
          setThemeState(nextTheme);
        }
      }
    };

    window.addEventListener("storage", handleStorage);
    return () => window.removeEventListener("storage", handleStorage);
  }, []);

  const setTheme = useCallback((newTheme: Theme) => {
    setThemeState(newTheme);
    safeStorage.setItem(STORAGE_KEY, newTheme);
  }, []);

  const toggleTheme = useCallback(() => {
    setThemeState((prev) => {
      const currentResolved =
        prev === "system"
          ? typeof window !== "undefined" && window.matchMedia("(prefers-color-scheme: dark)").matches
            ? "dark"
            : "light"
          : prev;
      const nextTheme: Theme = currentResolved === "dark" ? "light" : "dark";
      safeStorage.setItem(STORAGE_KEY, nextTheme);
      return nextTheme;
    });
  }, []);

  return (
    <ThemeContext.Provider value={{ theme, resolvedTheme, setTheme, toggleTheme }}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error("useTheme must be used within a ThemeProvider");
  }
  return context;
}
