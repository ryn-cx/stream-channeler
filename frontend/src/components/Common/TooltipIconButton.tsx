// TODO: Validate
import { Button } from "@/components/ui/button"
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip"
import { useIsTouchDevice } from "@/hooks/useMobile"
import { cn } from "@/lib/utils"

type ButtonSize = React.ComponentProps<typeof Button>["size"]

const LABELLED_SIZES: Record<string, ButtonSize> = {
  icon: "default",
  "icon-sm": "sm",
  "icon-lg": "lg",
}

interface TooltipIconButtonProps extends React.ComponentProps<typeof Button> {
  label: string
  icon: React.ReactNode
  /** Forces the label to render as button text (`true`) or to stay in the
   * tooltip (`false`). Left unset, touch devices show it and pointer devices
   * keep the tooltip. */
  showLabel?: boolean
}

// TODO: Validate
export function TooltipIconButton({
  label,
  icon,
  variant = "outline",
  size = "icon",
  type = "button",
  className,
  showLabel,
  ...props
}: TooltipIconButtonProps) {
  const isTouchDevice = useIsTouchDevice()
  const buttonClassName = cn("bg-muted dark:bg-muted/50", className)

  if (showLabel ?? isTouchDevice) {
    return (
      <Button
        variant={variant}
        size={LABELLED_SIZES[size ?? "icon"] ?? size}
        type={type}
        className={buttonClassName}
        {...props}
      >
        {icon}
        {label}
      </Button>
    )
  }

  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <Button
          variant={variant}
          size={size}
          type={type}
          className={buttonClassName}
          {...props}
        >
          {icon}
          <span className="sr-only">{label}</span>
        </Button>
      </TooltipTrigger>
      <TooltipContent>{label}</TooltipContent>
    </Tooltip>
  )
}
