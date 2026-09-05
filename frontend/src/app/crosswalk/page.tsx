"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function CrosswalkRedirectPage() {
  const router = useRouter();

  useEffect(() => {
    // Seamless forward to the unified National Master Directory
    router.replace("/materials?tab=GOLDEN");
  }, [router]);

  return (
    <div className="flex flex-col items-center justify-center py-24 space-y-3">
      <div className="h-5 w-5 border-2 border-zinc-900 dark:border-zinc-100 border-t-transparent rounded-full animate-spin" />
      <p className="text-xs text-zinc-500 font-mono">
        Routing to Unified National Master Directory...
      </p>
    </div>
  );
}
