import * as React from "react";

import { cn } from "../../lib/utils";

const Card = React.forwardRef(({ className, ...props }, ref) => {
  return <div ref={ref} className={cn("rounded-2xl border border-border/60 bg-card text-card-foreground shadow-card", className)} {...props} />;
});
Card.displayName = "Card";

const CardHeader = React.forwardRef(({ className, ...props }, ref) => {
  return <div ref={ref} className={cn("flex flex-col space-y-1.5 p-5", className)} {...props} />;
});
CardHeader.displayName = "CardHeader";

const CardTitle = React.forwardRef(({ className, ...props }, ref) => {
  return <h2 ref={ref} className={cn("text-[22px] font-semibold tracking-tight", className)} {...props} />;
});
CardTitle.displayName = "CardTitle";

const CardDescription = React.forwardRef(({ className, ...props }, ref) => {
  return <p ref={ref} className={cn("text-[15px] leading-relaxed text-muted-foreground", className)} {...props} />;
});
CardDescription.displayName = "CardDescription";

const CardContent = React.forwardRef(({ className, ...props }, ref) => {
  return <div ref={ref} className={cn("px-5 pb-5 pt-0", className)} {...props} />;
});
CardContent.displayName = "CardContent";

const CardFooter = React.forwardRef(({ className, ...props }, ref) => {
  return <div ref={ref} className={cn("flex items-center px-5 pb-5 pt-0", className)} {...props} />;
});
CardFooter.displayName = "CardFooter";

export { Card, CardHeader, CardFooter, CardTitle, CardDescription, CardContent };