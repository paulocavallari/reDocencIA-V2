import * as React from "react";
import * as AlertDialogPrimitive from "@radix-ui/react-alert-dialog";

import { buttonVariants } from "./button";
import { cn } from "../../lib/utils";

const AlertDialog = AlertDialogPrimitive.Root;
const AlertDialogTrigger = AlertDialogPrimitive.Trigger;
const AlertDialogPortal = AlertDialogPrimitive.Portal;

const AlertDialogOverlay = React.forwardRef(({ className, ...props }, ref) => {
  return <AlertDialogPrimitive.Overlay ref={ref} className={cn("fixed inset-0 z-50 bg-black/30 backdrop-blur-sm", className)} {...props} />;
});
AlertDialogOverlay.displayName = "AlertDialogOverlay";

const AlertDialogContent = React.forwardRef(({ className, ...props }, ref) => {
  return (
    <AlertDialogPortal>
      <AlertDialogOverlay />
      <AlertDialogPrimitive.Content
        ref={ref}
        className={cn("fixed left-1/2 top-1/2 z-50 grid w-[calc(100%-2rem)] max-w-sm -translate-x-1/2 -translate-y-1/2 gap-4 rounded-2xl bg-card p-6 shadow-elevated", className)}
        {...props}
      />
    </AlertDialogPortal>
  );
});
AlertDialogContent.displayName = "AlertDialogContent";

function AlertDialogHeader({ className, ...props }) {
  return <div className={cn("flex flex-col space-y-2 text-center", className)} {...props} />;
}

const AlertDialogTitle = React.forwardRef(({ className, ...props }, ref) => {
  return <AlertDialogPrimitive.Title ref={ref} className={cn("text-[17px] font-semibold text-foreground", className)} {...props} />;
});
AlertDialogTitle.displayName = "AlertDialogTitle";

const AlertDialogDescription = React.forwardRef(({ className, ...props }, ref) => {
  return <AlertDialogPrimitive.Description ref={ref} className={cn("text-[13px] leading-5 text-muted-foreground", className)} {...props} />;
});
AlertDialogDescription.displayName = "AlertDialogDescription";

function AlertDialogFooter({ className, ...props }) {
  return <div className={cn("flex flex-col gap-2", className)} {...props} />;
}

const AlertDialogAction = React.forwardRef(({ className, ...props }, ref) => {
  return <AlertDialogPrimitive.Action ref={ref} className={cn(buttonVariants({ variant: "destructive" }), "w-full", className)} {...props} />;
});
AlertDialogAction.displayName = "AlertDialogAction";

const AlertDialogCancel = React.forwardRef(({ className, ...props }, ref) => {
  return <AlertDialogPrimitive.Cancel ref={ref} className={cn(buttonVariants({ variant: "ghost" }), "w-full text-primary", className)} {...props} />;
});
AlertDialogCancel.displayName = "AlertDialogCancel";

export {
  AlertDialog,
  AlertDialogTrigger,
  AlertDialogContent,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogAction,
  AlertDialogCancel,
};