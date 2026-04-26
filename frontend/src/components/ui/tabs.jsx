import * as React from "react";
import * as TabsPrimitive from "@radix-ui/react-tabs";

import { cn } from "../../lib/utils";

const Tabs = TabsPrimitive.Root;

const TabsList = React.forwardRef(({ className, ...props }, ref) => {
  return <TabsPrimitive.List ref={ref} className={cn("inline-flex h-auto w-fit items-center gap-1 rounded-[10px] bg-secondary p-1", className)} {...props} />;
});
TabsList.displayName = "TabsList";

const TabsTrigger = React.forwardRef(({ className, ...props }, ref) => {
  return (
    <TabsPrimitive.Trigger
      ref={ref}
      className={cn(
        "inline-flex min-h-9 items-center justify-center rounded-lg px-4 py-2 text-[13px] font-medium text-muted-foreground transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 data-[state=active]:bg-white data-[state=active]:text-foreground data-[state=active]:shadow-subtle",
        className,
      )}
      {...props}
    />
  );
});
TabsTrigger.displayName = "TabsTrigger";

const TabsContent = React.forwardRef(({ className, ...props }, ref) => {
  return <TabsPrimitive.Content ref={ref} className={cn("outline-none", className)} {...props} />;
});
TabsContent.displayName = "TabsContent";

export { Tabs, TabsList, TabsTrigger, TabsContent };