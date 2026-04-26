import * as React from "react";
import * as DialogPrimitive from "@radix-ui/react-dialog";
import { X } from "lucide-react";

import { cn } from "../../lib/utils";

const Sheet = DialogPrimitive.Root;
const SheetTrigger = DialogPrimitive.Trigger;
const SheetClose = DialogPrimitive.Close;
const SheetPortal = DialogPrimitive.Portal;

const SheetOverlay = React.forwardRef(({ className, ...props }, ref) => {
  return <DialogPrimitive.Overlay ref={ref} className={cn("fixed inset-0 z-50 bg-black/25 backdrop-blur-sm", className)} {...props} />;
});
SheetOverlay.displayName = "SheetOverlay";

const SheetContent = React.forwardRef(({ className, children, side = "right", ...props }, ref) => {
  return (
    <SheetPortal>
      <SheetOverlay />
      <DialogPrimitive.Content
        ref={ref}
        className={cn(
          "fixed z-50 flex flex-col gap-4 bg-card p-5 shadow-elevated transition ease-in-out",
          side === "right" && "inset-y-0 right-0 h-full w-[88vw] max-w-sm rounded-l-2xl",
          side === "left" && "inset-y-0 left-0 h-full w-[88vw] max-w-sm rounded-r-2xl",
          className,
        )}
        {...props}
      >
        {children}
        <DialogPrimitive.Close className="absolute right-4 top-4 rounded-full p-2 text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground">
          <X className="h-4 w-4" />
          <span className="sr-only">Fechar</span>
        </DialogPrimitive.Close>
      </DialogPrimitive.Content>
    </SheetPortal>
  );
});
SheetContent.displayName = "SheetContent";

function SheetHeader({ className, ...props }) {
  return <div className={cn("flex flex-col space-y-2 text-left", className)} {...props} />;
}

const SheetTitle = React.forwardRef(({ className, ...props }, ref) => {
  return <DialogPrimitive.Title ref={ref} className={cn("text-[17px] font-semibold text-foreground", className)} {...props} />;
});
SheetTitle.displayName = "SheetTitle";

const SheetDescription = React.forwardRef(({ className, ...props }, ref) => {
  return <DialogPrimitive.Description ref={ref} className={cn("text-[15px] text-muted-foreground", className)} {...props} />;
});
SheetDescription.displayName = "SheetDescription";

export { Sheet, SheetTrigger, SheetClose, SheetContent, SheetHeader, SheetTitle, SheetDescription };