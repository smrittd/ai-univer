import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import { ButtonHTMLAttributes, forwardRef } from "react";
import { cn } from "@/lib/utils";

const variants = cva("inline-flex items-center justify-center rounded-lg px-4 py-2 font-semibold transition focus:outline-none focus:ring-2 focus:ring-cyan-400 disabled:opacity-50", {
  variants: { variant: { default: "bg-cyan-400 text-slate-950 hover:bg-cyan-300", outline: "border border-slate-600 hover:bg-slate-800" } },
  defaultVariants: { variant: "default" },
});

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement>, VariantProps<typeof variants> { asChild?: boolean }
export const Button = forwardRef<HTMLButtonElement, ButtonProps>(({ className, variant, asChild, ...props }, ref) => {
  const Comp = asChild ? Slot : "button";
  return <Comp className={cn(variants({ variant }), className)} ref={ref} {...props} />;
});
Button.displayName = "Button";
