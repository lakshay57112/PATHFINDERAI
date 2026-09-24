"use client";

import * as DialogPrimitive from "@radix-ui/react-dialog";
import { X } from "lucide-react";
import * as React from "react";
import { cn } from "@/lib/utils";

export const Dialog = DialogPrimitive.Root;
export const DialogTrigger = DialogPrimitive.Trigger;
export const DialogClose = DialogPrimitive.Close;
export const DialogTitle = DialogPrimitive.Title;
export const DialogDescription = DialogPrimitive.Description;

function Overlay() {
  return (
    <DialogPrimitive.Overlay className="fixed inset-0 z-50 bg-black/20 backdrop-blur-[2px] data-[state=open]:animate-[fade-up_.2s_ease_both]" />
  );
}

export function DialogContent({ className, children, ...props }: React.ComponentPropsWithoutRef<typeof DialogPrimitive.Content>) {
  return (
    <DialogPrimitive.Portal>
      <Overlay />
      <DialogPrimitive.Content
        className={cn(
          "fixed left-1/2 top-1/2 z-50 max-h-[88vh] w-[calc(100%-2rem)] max-w-lg -translate-x-1/2 -translate-y-1/2 overflow-y-auto rounded-2xl border border-line bg-surface p-6 shadow-lift focus:outline-none",
          className,
        )}
        {...props}
      >
        {children}
        <DialogPrimitive.Close className="focus-ring absolute right-4 top-4 rounded-md p-1 text-muted transition-colors hover:text-fg" aria-label="Close">
          <X className="size-4" />
        </DialogPrimitive.Close>
      </DialogPrimitive.Content>
    </DialogPrimitive.Portal>
  );
}

/** Right-side sheet (used for the global AI mentor). */
export function SheetContent({ className, children, ...props }: React.ComponentPropsWithoutRef<typeof DialogPrimitive.Content>) {
  return (
    <DialogPrimitive.Portal>
      <Overlay />
      <DialogPrimitive.Content
        className={cn(
          "fixed inset-y-0 right-0 z-50 flex w-full max-w-[460px] flex-col border-l border-line bg-background shadow-lift focus:outline-none",
          "data-[state=open]:animate-[sheet-in_.35s_cubic-bezier(.2,.7,.2,1)_both]",
          className,
        )}
        {...props}
      >
        {children}
      </DialogPrimitive.Content>
    </DialogPrimitive.Portal>
  );
}
