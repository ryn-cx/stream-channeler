// TODO: Validate
import { LayoutGrid, Table as TableIcon } from "lucide-react"

import { Button } from "@/components/ui/button"

export type ViewMode = "table" | "browse"

// Matches the channel detail page's switcher: one button naming the view it
// switches to, rather than a tab per view.
// TODO: Validate
export function ViewModeToggle({
  value,
  onValueChange,
}: {
  value: ViewMode
  onValueChange: (mode: ViewMode) => void
}) {
  const nextMode: ViewMode = value === "browse" ? "table" : "browse"

  return (
    <Button
      variant="outline"
      onClick={() => onValueChange(nextMode)}
      title={
        nextMode === "table" ? "Switch to table view" : "Switch to browse view"
      }
    >
      {nextMode === "table" ? <TableIcon /> : <LayoutGrid />}
      {nextMode === "table" ? "Table" : "Browse"}
    </Button>
  )
}
