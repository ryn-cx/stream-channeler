// TODO: Validate
import { DialogContent } from "@/components/ui/dialog"

const widths = {
  sm: "40%",
  md: "45%",
  lg: "50%",
  xl: "55%",
  "2xl": "60%",
  "3xl": "65%",
  "4xl": "70%",
  "5xl": "75%",
  "6xl": "80%",
  // As wide as the page leaves room for, for modals holding a full layout.
  full: "95%",
} as const

export type ModalSize = keyof typeof widths

interface ModalContentProps extends React.ComponentProps<typeof DialogContent> {
  /** Width of the modal. Defaults to `lg`; override for wider dialogs. */
  size?: ModalSize
}

// TODO: Validate
/**
 * Shared dialog body that gives every modal the same width and scroll
 * behavior. The `size` prop tweaks the width when a specific modal needs to be
 * wider or narrower than the default.
 */
export function ModalContent({ size = "lg", ...props }: ModalContentProps) {
  return <DialogContent width={widths[size]} {...props} />
}
