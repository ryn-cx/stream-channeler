// TODO: Validate
import { Link } from "@tanstack/react-router"
import { ExternalLink, SquareArrowOutUpRight } from "lucide-react"
import type { ReactNode } from "react"

import { Button } from "@/components/ui/button"
import useAuth from "@/hooks/useAuth"

/** A page this site holds a row on, and what names the row on it. */
type MediaPage =
  | { to: "/seasons"; search: { show_id: string } }
  | { to: "/episodes"; search: { season_id: string } }
  | { to: "/shows"; search: { source_id: string } }

// TODO: Validate
/**
 * The button that opens a row's own page, for an admin only.
 *
 * Beside the control that marks the row, since deciding a row is wrong is most
 * often what sends somebody to go and fix it. Opened in a window of its own so
 * the marks being made here are not lost on the way.
 *
 * An episode has no page of its own: episodes are edited from the table their
 * season holds, so an episode opens that.
 */
export function MediaPageButton({
  label,
  ...page
}: MediaPage & { label: string }) {
  const { user } = useAuth()
  if (!user?.is_superuser) return null

  return (
    <Button asChild variant="ghost" size="icon-sm" title={label}>
      <Link {...page} target="_blank" rel="noopener noreferrer">
        <SquareArrowOutUpRight className="h-4 w-4" />
        <span className="sr-only">{label}</span>
      </Link>
    </Button>
  )
}

// TODO: Validate
/**
 * The link out to the site the row came from, where it says where it is.
 *
 * Shown to anybody rather than admins alone, since following a title back to
 * where it is watched is no more than the row already says.
 */
export function ExternalMediaLink({
  url,
  label,
}: {
  url: string | null | undefined
  label: string
}) {
  if (!url) return null
  return (
    <Button asChild variant="ghost" size="icon-sm" title={label}>
      <a href={url} target="_blank" rel="noopener noreferrer">
        <ExternalLink className="h-4 w-4" />
        <span className="sr-only">{label}</span>
      </a>
    </Button>
  )
}

// TODO: Validate
/** Anything only an admin is shown, on a row an ordinary user reads too. */
export function AdminOnly({ children }: { children: ReactNode }) {
  const { user } = useAuth()
  if (!user?.is_superuser) return null
  return <>{children}</>
}
