import type { useReactTable } from "@tanstack/react-table"
import { ChevronsUpDown } from "lucide-react"

import { Input } from "@/components/ui/input"
import { Skeleton } from "@/components/ui/skeleton"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { cn } from "@/lib/utils"
import {
  TABLE_FILTER_INPUT_CLASS,
  TABLE_HEADER_CELL_CLASS,
} from "./tableStyles"

interface DataTableSkeletonProps<TData> {
  table: ReturnType<typeof useReactTable<TData>>
  rows?: number
}

/**
 * Loading skeleton for a `DataTable`. It is driven by the same table instance,
 * so its header row mirrors the real columns — including which ones are hidden
 * via column visibility — and matches the live header's sort/filter layout.
 */
export function DataTableSkeleton<TData>({
  table,
  rows = 5,
}: DataTableSkeletonProps<TData>) {
  const columns = table.getVisibleLeafColumns()
  const rowKeys = Array.from(
    { length: rows },
    (_, index) => `skeleton-${index}`,
  )

  return (
    <Table>
      <TableHeader>
        <TableRow className="hover:bg-transparent">
          {columns.map((column) => {
            const header = column.columnDef.header
            const label = typeof header === "string" ? header : ""
            const filterVariant = column.columnDef.meta?.filterVariant

            return (
              <TableHead key={column.id} className="align-top">
                <div className={TABLE_HEADER_CELL_CLASS}>
                  {label ? (
                    <div className="flex items-center gap-1">
                      {label}
                      {column.getCanSort() ? (
                        <ChevronsUpDown className="size-3.5 opacity-50" />
                      ) : null}
                    </div>
                  ) : (
                    <span className="sr-only">Actions</span>
                  )}
                  {column.getCanFilter() ? (
                    filterVariant === "select" ? (
                      <select
                        disabled
                        className={cn(
                          TABLE_FILTER_INPUT_CLASS,
                          "rounded border px-1",
                        )}
                      >
                        <option>All</option>
                      </select>
                    ) : (
                      <>
                        <Input
                          disabled
                          placeholder="Search..."
                          className={cn(TABLE_FILTER_INPUT_CLASS, "w-36")}
                        />
                        {/* Matches the live text filter's trailing spacer so
                            the header row height lines up exactly. */}
                        <div className="h-1" />
                      </>
                    )
                  ) : null}
                </div>
              </TableHead>
            )
          })}
        </TableRow>
      </TableHeader>
      <TableBody>
        {rowKeys.map((rowKey) => (
          <TableRow key={rowKey}>
            {columns.map((column) => (
              <TableCell key={column.id}>
                {column.id === "actions" ? (
                  <div className="flex items-center justify-end gap-1">
                    <Skeleton className="size-8 rounded-md" />
                    <Skeleton className="size-8 rounded-md" />
                  </div>
                ) : (
                  <Skeleton className="h-4 w-full max-w-48" />
                )}
              </TableCell>
            ))}
          </TableRow>
        ))}
      </TableBody>
    </Table>
  )
}
