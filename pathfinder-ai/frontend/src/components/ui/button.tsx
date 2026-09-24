import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import { Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "focus-ring inline-flex select-none items-center justify-center gap-2 whitespace-nowrap font-medium transition-[transform,background-color,border-color,color,box-shadow] duration-200 ease-[cubic-bezier(.2,.7,.2,1)] hover:scale-[1.01] active:scale-[0.98] disabled:pointer-events-none disabled:opacity-40 [&_svg]:size-4 [&_svg]:shrink-0",
  {
    variants: {
      variant: {
        primary: "bg-ink text-white hover:bg-[#1f1f1f] shadow-[0_1px_0_rgba(255,255,255,0.12)_inset,0_1px_2px_rgba(0,0,0,0.2)]",
        secondary: "border border-line-strong bg-surface text-fg hover:border-[#bdbdbd] hover:bg-surface-2",
        ghost: "text-fg-2 hover:bg-surface-2 hover:text-fg",
        link: "text-fg underline-offset-4 hover:underline hover:scale-100",
        danger: "border border-danger/30 bg-surface text-danger hover:bg-danger/5",
      },
      size: {
        sm: "h-8 rounded-lg px-3 text-[13px]",
        md: "h-10 rounded-lg px-4 text-sm",
        lg: "h-12 rounded-xl px-6 text-[15px]",
        pill: "h-12 rounded-full px-7 text-[15px]",
        icon: "h-9 w-9 rounded-lg",
      },
    },
    defaultVariants: { variant: "primary", size: "md" },
  },
);

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement>, VariantProps<typeof buttonVariants> {
  asChild?: boolean;
  loading?: boolean;
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild, loading, children, disabled, ...props }, ref) => {
    const Comp = asChild ? Slot : "button";
    return (
      <Comp ref={ref} className={cn(buttonVariants({ variant, size }), className)} disabled={disabled || loading} {...props}>
        {asChild ? children : (
          <>
            {loading && <Loader2 className="animate-spin" aria-hidden />}
            {children}
          </>
        )}
      </Comp>
    );
  },
);
Button.displayName = "Button";

export { buttonVariants };
