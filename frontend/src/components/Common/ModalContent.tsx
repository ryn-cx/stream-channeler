import { DialogContent } from "@/components/ui/dialog"
import { cn } from "@/lib/utils"

/**
 * Tailwind can't build class names dynamically, so the allowed widths are
 * mapped explicitly. Add an entry here to expose a new modal width.
 */
const widthClasses = {
  sm: "sm:max-w-sm",
  md: "sm:max-w-md",
  lg: "sm:max-w-lg",
  xl: "sm:max-w-xl",
  "2xl": "sm:max-w-2xl",
  "3xl": "sm:max-w-3xl",
  "4xl": "sm:max-w-4xl",
  "5xl": "sm:max-w-5xl",
} as const

export type ModalSize = keyof typeof widthClasses

interface ModalContentProps extends React.ComponentProps<typeof DialogContent> {
  /** Width of the modal. Defaults to `lg`; override for wider dialogs. */
  size?: ModalSize
}

/**
 * Shared dialog body that gives every modal the same width and scroll
 * behavior. The `size` prop tweaks the width when a specific modal needs to be
 * wider or narrower than the default.
 */
export function ModalContent({
  size = "lg",
  className,
  ...props
}: ModalContentProps) {
  return (
    <DialogContent
      className={cn(
        widthClasses[size],
        "max-h-[80vh] overflow-y-auto",
        className,
      )}
      {...props}
    />
  )
}
