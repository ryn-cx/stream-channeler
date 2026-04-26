// TODO: Validate
import type { useReactTable } from "@tanstack/react-table"
import { Columns } from "lucide-react"
import { useState } from "react"

import { VariantTrigger } from "@/components/Common/VariantTrigger"
import {
  DropdownMenu,
  DropdownMenuCheckboxItem,
  DropdownMenuContent,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"

interface ColumnVisibilityButtonProps<TData> {
  table: ReturnType<typeof useReactTable<TData>>
  variant?: "button" | "menu"
}

export function ColumnVisibilityButton<TData>({
  table,
  variant = "button",
}: ColumnVisibilityButtonProps<TData>) {
  const [isOpen, setIsOpen] = useState(false)

  return (
    // From: https://ui.shadcn.com/docs/components/dropdown-menu
    <DropdownMenu open={isOpen} onOpenChange={setIsOpen}>
      <DropdownMenuTrigger asChild>
        <VariantTrigger variant={variant} icon={Columns} label="Columns" />
      </DropdownMenuTrigger>
      <DropdownMenuContent className="w-56">
        <DropdownMenuLabel>Toggle columns</DropdownMenuLabel>
        <DropdownMenuSeparator />
        {/* From: https://tanstack.com/table/v8/docs/framework/react/examples/column-visibility */}
        <DropdownMenuCheckboxItem
          checked={table.getIsAllColumnsVisible()}
          onCheckedChange={table.getToggleAllColumnsVisibilityHandler()}
          // Don't automatically close the menu when clicking this button
          onSelect={(e) => e.preventDefault()}
        >
          Toggle All
        </DropdownMenuCheckboxItem>
        <DropdownMenuSeparator />
        {/* From: https://tanstack.com/table/v8/docs/framework/react/examples/column-visibility */}
        {table.getAllLeafColumns().map((column) => {
          const header = column.columnDef.header
          const displayName = typeof header === "string" ? header : column.id

          return (
            <DropdownMenuCheckboxItem
              key={column.id}
              checked={column.getIsVisible()}
              onCheckedChange={() => column.toggleVisibility()}
              // Don't automatically close the menu when clicking this button
              onSelect={(e) => e.preventDefault()}
            >
              {displayName}
            </DropdownMenuCheckboxItem>
          )
        })}
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
