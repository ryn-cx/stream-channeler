// TODO: Validate
import { Link } from "@tanstack/react-router"

interface CellProps {
  value: string | null | undefined
}

type ParentLinkCellProps =
  | {
      to: "/season/$seasonKey"
      params: { seasonKey: string }
      name: string | null
    }
  | { to: "/show/$showKey"; params: { showKey: string }; name: string | null }
  | {
      to: "/source/$sourceKey"
      params: { sourceKey: string }
      name: string | null
    }
  | {
      to: "/plugin/$pluginId"
      params: { pluginId: string }
      name: string | null
    }

// TODO: Validate
export function ParentLinkCell({ to, params, name }: ParentLinkCellProps) {
  return (
    <Link
      to={to}
      params={params}
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
