// TODO: Validate
import type { ComponentProps } from "react"

import { TabsList } from "@/components/ui/tabs"
import { cn } from "@/lib/utils"

// TODO: Validate
export function WrappingTabsList({
  className,
  ...props
}: ComponentProps<typeof TabsList>) {
  return (
    <TabsList
      className={cn(
        "h-auto w-fit max-w-full shrink-0 self-center flex-wrap justify-center gap-1",
        // A tab is as wide as its own name. Too many for one row wrap onto
        // the next rather than being squeezed together or scrolled out of
        // sight.
        "*:flex-none *:shrink-0",
        className,
      )}
      {...props}
    />
  )
}
