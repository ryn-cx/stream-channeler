// TODO: Validate
import type { ReactNode } from "react"

import { cn } from "@/lib/utils"

// TODO: Validate
/**
 * A part of an ordinary page that only an admin is shown.
 *
 * An edit form is mostly a user editing their own thing, and the fields an
 * admin gets are mixed in among them looking exactly the same. What is done in
 * those reaches past the one row being edited - a channel's score orders it
 * against everybody else's, a TMDB link is the record every website's
 * non-canonical row is
 * matched to - so they are marked out rather than left to look ordinary.
 */
export function AdminZone({
  children,
  className,
}: {
  children: ReactNode
  className?: string
}) {
  return (
    <div
      className={cn(
        "space-y-2 rounded-md border border-dashed border-blue-900 bg-blue-900/10 p-3 dark:border-blue-500 dark:bg-blue-500/25",
        className,
      )}
    >
      {children}
    </div>
  )
}
