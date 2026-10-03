// TODO: Validate
import type { useReactTable } from "@tanstack/react-table"
import { Columns } from "lucide-react"
import { useState } from "react"

import { VariantTrigger } from "@/components/Common/VariantTrigger"
import { Checkbox } from "@/components/ui/checkbox"
import {
  Dialog,
  DialogBody,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import {
  DropdownMenu,
  DropdownMenuCheckboxItem,
  DropdownMenuContent,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { Label } from "@/components/ui/label"

interface ColumnVisibilityButtonProps<TData> {
  table: ReturnType<typeof useReactTable<TData>>
  variant?: "button" | "menu"
  open?: boolean
  onOpenChange?: (open: boolean) => void
  hideTrigger?: boolean
}

// TODO: Validate
export function ColumnVisibilityButton<TData>({
  table,
  variant = "button",
  open,
  onOpenChange,
  hideTrigger,
}: ColumnVisibilityButtonProps<TData>) {
  const [internalOpen, setInternalOpen] = useState(false)
  const isOpen = open ?? internalOpen
  const setIsOpen = onOpenChange ?? setInternalOpen

  if (hideTrigger) {
    return (
      <Dialog open={isOpen} onOpenChange={setIsOpen}>
        <DialogContent className="sm:max-w-sm">
          <DialogHeader>
            <DialogTitle>Toggle columns</DialogTitle>
            <DialogDescription>
              Choose which columns the table shows.
            </DialogDescription>
          </DialogHeader>
          <DialogBody className="flex flex-col gap-3">
            <div className="flex items-center gap-2">
              <Checkbox
                id="column-visibility-all"
                checked={table.getIsAllColumnsVisible()}
                onCheckedChange={() =>
                  table.toggleAllColumnsVisible(!table.getIsAllColumnsVisible())
                }
              />
              <Label htmlFor="column-visibility-all">Toggle All</Label>
            </div>
            {table.getAllLeafColumns().map((column) => {
              const header = column.columnDef.header
              const displayName =
                typeof header === "string" ? header : column.id

              return (
                <div key={column.id} className="flex items-center gap-2">
                  <Checkbox
                    id={`column-visibility-${column.id}`}
                    checked={column.getIsVisible()}
                    onCheckedChange={() => column.toggleVisibility()}
                  />
                  <Label htmlFor={`column-visibility-${column.id}`}>
                    {displayName}
                  </Label>
                </div>
              )
            })}
          </DialogBody>
        </DialogContent>
      </Dialog>
    )
  }

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
