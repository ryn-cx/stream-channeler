// TODO: Validate
import { LayoutGrid, Table as TableIcon, Tv } from "lucide-react"

import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"

export type ViewMode = "table" | "browse" | "guide"

// TODO: Validate
export function ViewModeToggle({
  value,
  onValueChange,
  modes = ["browse", "table"],
}: {
  value: ViewMode
  onValueChange: (mode: ViewMode) => void
  modes?: ViewMode[]
}) {
  const details = {
    table: { label: "Table", icon: TableIcon },
    browse: { label: "Browse", icon: LayoutGrid },
    guide: { label: "Guide", icon: Tv },
  }

  return (
    <Tabs
      value={value}
      onValueChange={(next) => onValueChange(next as ViewMode)}
    >
      <TabsList>
        {modes.map((mode) => {
          const { label, icon: Icon } = details[mode]
          return (
            <TabsTrigger
              key={mode}
              value={mode}
              title={`Switch to ${label.toLowerCase()} view`}
            >
              <Icon className="size-4" />
              {label}
            </TabsTrigger>
          )
        })}
      </TabsList>
    </Tabs>
  )
}
