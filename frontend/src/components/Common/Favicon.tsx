// TODO: Validate
import type { ComponentProps } from "react"
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip"
import { cn } from "@/lib/utils"

// TODO: Validate
export function Favicon({
  src,
  label,
  className,
  tooltip = true,
  ...props
}: ComponentProps<"img"> & {
  src: string
  label: string
  tooltip?: boolean
}) {
  const image = (
    <img
      referrerPolicy="no-referrer"
      loading="lazy"
      src={src}
      alt={label}
      className={cn("size-4 shrink-0", className)}
      {...props}
    />
  )
  if (!tooltip) {
    return image
  }
  return (
    <Tooltip>
      <TooltipTrigger asChild>{image}</TooltipTrigger>
      <TooltipContent>{label}</TooltipContent>
    </Tooltip>
  )
}
