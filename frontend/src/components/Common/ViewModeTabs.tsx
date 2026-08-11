// TODO: Validate
import { LayoutGrid, Table as TableIcon } from "lucide-react"

import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"

export type ViewMode = "table" | "browse"

// Sits beside the scope tabs and matches them, so both views are visible and
// directly clickable instead of hiding behind a single toggling button.
// TODO: Validate
export function ViewModeTabs({
  value,
  onValueChange,
}: {
  value: ViewMode
  onValueChange: (mode: ViewMode) => void
}) {
  return (
    <Tabs
      value={value}
      onValueChange={(mode) => onValueChange(mode as ViewMode)}
    >
      <TabsList>
        <TabsTrigger value="browse">
          <LayoutGrid />
          Browse
        </TabsTrigger>
        <TabsTrigger value="table">
          <TableIcon />
          Table
        </TabsTrigger>
      </TabsList>
    </Tabs>
  )
}
