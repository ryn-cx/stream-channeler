// TODO: Validate
import { Link } from "@tanstack/react-router"

interface CellProps {
  value: string | null | undefined
}

type ParentLinkCellProps =
  | {
      to: "/episodes"
      search: { season_id: string }
      name: string | null
    }
  | { to: "/seasons"; search: { show_id: string }; name: string | null }
  | {
      to: "/shows"
      search: { source_id: string }
      name: string | null
    }
  | {
      to: "/sources"
      search: { plugin_id: string }
      name: string | null
    }

// TODO: Validate
export function ParentLinkCell({ to, search, name }: ParentLinkCellProps) {
  return (
    <Link
      to={to}
      search={search}
      className="text-primary hover:underline text-sm truncate max-w-40 block"
    >
      {name || "Unnamed"}
    </Link>
  )
}

// TODO: Validate
export function TruncatedCell({ value }: CellProps) {
  return (
    <span className="text-muted-foreground text-sm truncate max-w-48 block">
      {value ?? "-"}
    </span>
  )
}

// TODO: Validate
export function DateCell({ value }: CellProps) {
  return (
    <span className="text-muted-foreground text-sm">
      {value ? new Date(value).toLocaleString() : "-"}
    </span>
  )
}
