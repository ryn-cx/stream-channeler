// TODO: Validate
import type { ReactNode } from "react"

import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip"

interface TooltipIconLinkProps {
  label: string
  children: ReactNode
}

// TODO: Validate
export function TooltipIconLink({ label, children }: TooltipIconLinkProps) {
  return (
    <Tooltip>
      <TooltipTrigger asChild>{children}</TooltipTrigger>
      <TooltipContent>{label}</TooltipContent>
    </Tooltip>
  )
}
