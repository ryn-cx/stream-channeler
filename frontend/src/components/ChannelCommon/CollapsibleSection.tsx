// TODO: Validate
import { ChevronDown, ChevronRight } from "lucide-react"
import { type ReactNode, useState } from "react"

import { Button } from "@/components/ui/button"

interface CollapsibleSectionProps {
  title: string
  children: ReactNode
  defaultOpen?: boolean
}

// TODO: Validate
/**
 * A section that stays out of the way until it is asked for.
 *
 * The field-by-field comparison is there to be checked rather than read, so it
 * is closed until someone goes looking for it.
 */
export function CollapsibleSection({
  title,
  children,
  defaultOpen = false,
}: CollapsibleSectionProps) {
  const [open, setOpen] = useState(defaultOpen)

  return (
    <div className="rounded border">
      <button
        type="button"
        className="flex w-full items-center gap-2 p-2 text-left hover:bg-accent/30"
        onClick={() => setOpen(!open)}
      >
        <Button variant="ghost" size="icon-sm" asChild>
          <span>
            {open ? (
              <ChevronDown className="h-4 w-4" />
            ) : (
              <ChevronRight className="h-4 w-4" />
            )}
          </span>
        </Button>
        <span className="text-sm font-medium">{title}</span>
      </button>
      {open && <div className="border-t p-2">{children}</div>}
    </div>
  )
}
