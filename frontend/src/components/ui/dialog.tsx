// TODO: Validate
import * as React from "react"

import { WinBoxModal } from "@/components/Common/WinBoxModal"
import { cn } from "@/lib/utils"

interface DialogContextValue {
  open: boolean
  setOpen: (open: boolean) => void
  title: string
  setTitle: React.Dispatch<React.SetStateAction<string>>
}

const DialogContext = React.createContext<DialogContextValue | null>(null)

// TODO: Validate
function useDialogContext(): DialogContextValue {
  const context = React.useContext(DialogContext)
  if (!context) {
    throw new Error("Dialog parts have to be rendered inside a Dialog")
  }
  return context
}

interface DialogProps {
  open?: boolean
  defaultOpen?: boolean
  onOpenChange?: (open: boolean) => void
  modal?: boolean
  children?: React.ReactNode
}

// TODO: Validate
function Dialog({ open, defaultOpen, onOpenChange, children }: DialogProps) {
  const [uncontrolledOpen, setUncontrolledOpen] = React.useState(
    defaultOpen ?? false,
  )
  const [title, setTitle] = React.useState("")

  const setOpen = React.useCallback(
    (next: boolean) => {
      setUncontrolledOpen(next)
      onOpenChange?.(next)
    },
    [onOpenChange],
  )

  const value = React.useMemo(
    () => ({ open: open ?? uncontrolledOpen, setOpen, title, setTitle }),
    [open, uncontrolledOpen, setOpen, title],
  )

  return (
    <DialogContext.Provider value={value}>{children}</DialogContext.Provider>
  )
}

type ToggleProps = React.ComponentProps<"button"> & { asChild?: boolean }

type DialogToggleProps = ToggleProps & { slot: string; nextOpen: boolean }

// TODO: Validate
function DialogToggle({
  asChild,
  children,
  onClick,
  slot,
  nextOpen,
  ...props
}: DialogToggleProps) {
  const { setOpen } = useDialogContext()

  if (
    asChild &&
    React.isValidElement<React.ComponentProps<"button">>(children)
  ) {
    return React.cloneElement(children, {
      onClick: (event: React.MouseEvent<HTMLButtonElement>) => {
        children.props.onClick?.(event)
        setOpen(nextOpen)
      },
    })
  }

  return (
    <button
      type="button"
      data-slot={slot}
      onClick={(event) => {
        onClick?.(event)
        setOpen(nextOpen)
      }}
      {...props}
    >
      {children}
    </button>
  )
}

// TODO: Validate
function DialogTrigger(props: ToggleProps) {
  return <DialogToggle slot="dialog-trigger" nextOpen={true} {...props} />
}

// TODO: Validate
function DialogClose(props: ToggleProps) {
  return <DialogToggle slot="dialog-close" nextOpen={false} {...props} />
}

// TODO: Validate
function DialogPortal({ children }: { children?: React.ReactNode }) {
  return <>{children}</>
}

// TODO: Validate
function DialogOverlay(_props: React.ComponentProps<"div">) {
  return null
}

type DialogContentProps = React.ComponentProps<"div"> & {
  showCloseButton?: boolean
  width?: string
  height?: string
}

// TODO: Validate
function DialogContent({
  className,
  children,
  width,
  height,
}: DialogContentProps) {
  const { open, setOpen, title } = useDialogContext()

  return (
    <WinBoxModal
      open={open}
      title={title}
      onClose={() => setOpen(false)}
      width={width}
      height={height}
      className={cn("flex flex-col gap-4 p-6", className)}
    >
      {children}
    </WinBoxModal>
  )
}

// TODO: Validate
function DialogHeader({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="dialog-header"
      className={cn("flex shrink-0 flex-col gap-2 text-left", className)}
      {...props}
    />
  )
}

// TODO: Validate
function DialogBody({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="dialog-body"
      className={cn(
        "no-scrollbar -mx-6 min-h-0 flex-1 overflow-y-auto px-6",
        className,
      )}
      {...props}
    />
  )
}

// TODO: Validate
function DialogFooter({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="dialog-footer"
      className={cn(
        "flex shrink-0 flex-col-reverse gap-2 sm:flex-row sm:justify-end",
        className,
      )}
      {...props}
    />
  )
}

// TODO: Validate
function DialogTitle({ className, ...props }: React.ComponentProps<"h2">) {
  const { setTitle } = useDialogContext()
  const ref = React.useRef<HTMLHeadingElement>(null)

  React.useEffect(() => {
    const text = ref.current?.textContent ?? ""
    setTitle((previous) => (previous === text ? previous : text))
  })

  return (
    <h2
      ref={ref}
      data-slot="dialog-title"
      className={cn("sr-only", className)}
      {...props}
    />
  )
}

// TODO: Validate
function DialogDescription({ className, ...props }: React.ComponentProps<"p">) {
  return (
    <p
      data-slot="dialog-description"
      className={cn("text-muted-foreground text-sm", className)}
      {...props}
    />
  )
}

export {
  Dialog,
  DialogBody,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogOverlay,
  DialogPortal,
  DialogTitle,
  DialogTrigger,
}
