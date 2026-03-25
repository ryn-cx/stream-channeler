// TODO: Validate
import type { useReactTable } from "@tanstack/react-table"
import { Columns } from "lucide-react"
import { useState } from "react"

import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuCheckboxItem,
  DropdownMenuContent,
  DropdownMenuItem,
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
        {variant === "menu" ? (
          <DropdownMenuItem
            onSelect={(e) => {
              e.preventDefault()
            }}
          >
            <Columns className="mr-2 size-4" />
            Columns
          </DropdownMenuItem>
        ) : (
          <Button className="mt-2 mb-4">
            <Columns />
            Columns
          </Button>
        )}
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
