"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState } from "react";
import { Toaster } from "sonner";
import { TooltipProvider } from "@radix-ui/react-tooltip";

export function Providers({ children }: { children: React.ReactNode }) {
  const [client] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: { staleTime: 20_000, refetchOnWindowFocus: false, retry: 1 },
        },
      }),
  );
  return (
    <QueryClientProvider client={client}>
      <TooltipProvider delayDuration={200}>
        {children}
        <Toaster
          position="bottom-center"
          toastOptions={{
            className: "!rounded-xl !border !border-line !bg-surface !text-fg !shadow-lift !font-sans",
          }}
        />
      </TooltipProvider>
    </QueryClientProvider>
  );
}
