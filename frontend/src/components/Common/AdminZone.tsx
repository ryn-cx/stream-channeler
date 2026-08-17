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
 * matched to - so they are marked out rather than left to look ordinary. Tinted
 * the way the onboarding page tints what it warns about, so the two read as the
 * same kind of warning.
 */
export function AdminZone({
  children,
  label = "Admin only",
  className,
}: {
  children: ReactNode
  label?: string
  className?: string
}) {
  return (
    <div
      className={cn(
        "space-y-2 rounded-md border border-dashed border-destructive/40 bg-destructive/10 p-3 dark:bg-destructive/25",
        className,
      )}
    >
      <p className="text-xs font-medium text-destructive">{label}</p>
      {children}
    </div>
  )
}
