import {
  type Column,
  type ColumnDef,
  type ColumnFiltersState,
  flexRender,
  getCoreRowModel,
  getFacetedMinMaxValues,
  getFacetedRowModel,
  getFacetedUniqueValues,
  getFilteredRowModel,
  getPaginationRowModel,
  getSortedRowModel,
  type OnChangeFn,
  type PaginationState,
  type Row,
  type RowData,
  type SortingState,
  useReactTable,
  type VisibilityState,
} from "@tanstack/react-table"
import {
  ArrowDown,
  ArrowUp,
  ChevronLeft,
  ChevronRight,
  ChevronsLeft,
  ChevronsRight,
  ChevronsUpDown,
} from "lucide-react"
import { useCallback, useEffect, useMemo, useState } from "react"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
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

declare module "@tanstack/react-table" {
  interface ColumnMeta<TData extends RowData, TValue> {
    filterVariant?: "text" | "range" | "select" | "dateRange"
    serverFilter?: {
      value: string
      onChange: (value: string) => void
      placeholder?: string
    }
  }
}

interface DateRangeFilterValue {
  minimumDate?: string
  maximumDate?: string
  hideBlanks?: boolean
}

function dateRangeFilterFn<TData>(
  row: Row<TData>,
  columnId: string,
  filterValue: DateRangeFilterValue,
): boolean {
  const rawDate = row.getValue(columnId) as string | null | undefined
  const { minimumDate, maximumDate, hideBlanks } = filterValue ?? {}

  // Blank values should always be shown unless explicitly hidden.
  if (rawDate === null) return !hideBlanks

  const date = new Date(rawDate as string).getTime()

  if (minimumDate && date < new Date(minimumDate).getTime()) return false
  if (maximumDate && date > new Date(maximumDate).getTime()) return false
  return true
}

function usePersistentState<T>(key: string | undefined, initialValue: T) {
  const [value, setValue] = useState<T>(() => {
    if (!key) return initialValue
    try {
      const stored = sessionStorage.getItem(key)
      return stored ? (JSON.parse(stored) as T) : initialValue
    } catch {
      return initialValue
    }
  })

  useEffect(() => {
    if (!key) return
    try {
      sessionStorage.setItem(key, JSON.stringify(value))
    } catch {}
  }, [key, value])

  return [value, setValue] as const
}

interface DataTableProps<TData extends { id: string }, TValue> {
  columns: ColumnDef<TData, TValue>[]
  data: TData[]
  rowClassName?: (row: TData) => string | undefined
  storageKey?: string
  columnVisibility?: VisibilityState
  onColumnVisibilityChange?: OnChangeFn<VisibilityState>
}

export function DataTable<TData extends { id: string }, TValue>({
  columns,
  data,
  rowClassName,
  storageKey,
  columnVisibility,
  onColumnVisibilityChange,
}: DataTableProps<TData, TValue>) {
  const processedColumns = useMemo(
    () =>
      columns.map((column) =>
        column.meta?.filterVariant === "dateRange"
          ? { ...column, filterFn: dateRangeFilterFn }
          : column,
      ),
    [columns],
  )

  const [sorting, setSorting] = usePersistentState<SortingState>(
    storageKey && `${storageKey}:sorting`,
    [],
  )
  const [columnFilters, setColumnFilters] =
    usePersistentState<ColumnFiltersState>(
      storageKey && `${storageKey}:filters`,
      [],
    )
  const [pagination, setPagination] = usePersistentState<PaginationState>(
    storageKey && `${storageKey}:pagination`,
    { pageIndex: 0, pageSize: 10 },
  )

  // Reset page to 0 when filters actually change, since autoResetPageIndex
  // is disabled to prevent pagination clicks from resetting the page.
  const handleColumnFiltersChange: OnChangeFn<ColumnFiltersState> = useCallback(
    (updater) => {
      setColumnFilters((prev) => {
        const next = typeof updater === "function" ? updater(prev) : updater
        if (JSON.stringify(next) !== JSON.stringify(prev)) {
          setPagination((p) => ({ ...p, pageIndex: 0 }))
        }
        return next
      })
    },
    [setColumnFilters, setPagination],
  )

  const table = useReactTable({
    data,
    columns: processedColumns,
    getRowId: (row) => row.id,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(), //client-side filtering
    getPaginationRowModel: getPaginationRowModel(),
    getFacetedRowModel: getFacetedRowModel(), // client-side faceting
    getFacetedUniqueValues: getFacetedUniqueValues(), // generate unique values for select filter/autocomplete
    getFacetedMinMaxValues: getFacetedMinMaxValues(), // generate min/max values for range filter
    onSortingChange: setSorting,
    onColumnFiltersChange: handleColumnFiltersChange,
    onPaginationChange: setPagination,
    onColumnVisibilityChange,
    state: {
      sorting,
      columnFilters,
      pagination,
      columnVisibility,
    },
    autoResetPageIndex: false,
  })

  return (
    <div className="flex flex-col gap-4">
      <Table>
        <TableHeader>
          {table.getHeaderGroups().map((headerGroup) => (
            <TableRow key={headerGroup.id} className="hover:bg-transparent">
              {headerGroup.headers.map((header) => {
                const column = header.column

                return (
                  <TableHead key={header.id} className="align-top">
                    {header.isPlaceholder ? null : (
                      <div className={TABLE_HEADER_CELL_CLASS}>
                        <button
                          type="button"
                          className={
                            column.getCanSort()
                              ? "flex items-center gap-1 cursor-pointer select-none"
                              : "flex items-center gap-1"
                          }
                          onClick={column.getToggleSortingHandler()}
                          disabled={!column.getCanSort()}
                          title={
                            column.getCanSort()
                              ? column.getNextSortingOrder() === "asc"
                                ? "Sort ascending"
                                : column.getNextSortingOrder() === "desc"
                                  ? "Sort descending"
                                  : "Clear sort"
                              : undefined
                          }
                        >
                          {flexRender(
                            column.columnDef.header,
                            header.getContext(),
                          )}
                          {column.getCanSort() &&
                            (column.getIsSorted() === "asc" ? (
                              <ArrowUp className="size-3.5" />
                            ) : column.getIsSorted() === "desc" ? (
                              <ArrowDown className="size-3.5" />
                            ) : (
                              <ChevronsUpDown className="size-3.5 opacity-50" />
                            ))}
                        </button>
                        {column.getCanFilter() ? (
                          <Filter column={column} />
                        ) : null}
                      </div>
                    )}
                  </TableHead>
                )
              })}
            </TableRow>
          ))}
        </TableHeader>
        <TableBody>
          {table.getRowModel().rows.length ? (
            table.getRowModel().rows.map((row) => (
              <TableRow key={row.id} className={rowClassName?.(row.original)}>
                {row.getVisibleCells().map((cell) => (
                  <TableCell key={cell.id}>
                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                  </TableCell>
                ))}
              </TableRow>
            ))
          ) : (
            <TableRow className="hover:bg-transparent">
              <TableCell
                colSpan={table.getVisibleLeafColumns().length}
                className="h-32 text-center text-muted-foreground"
              >
                No results found.
              </TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>

      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 p-4 border-t bg-muted/20">
        <div className="flex flex-col sm:flex-row sm:items-center gap-4">
          <div className="text-sm text-muted-foreground">
            Showing{" "}
            {table.getState().pagination.pageIndex *
              table.getState().pagination.pageSize +
              1}{" "}
            to{" "}
            {Math.min(
              (table.getState().pagination.pageIndex + 1) *
                table.getState().pagination.pageSize,
              table.getFilteredRowModel().rows.length,
            )}{" "}
            of{" "}
            <span className="font-medium text-foreground">
              {table.getFilteredRowModel().rows.length}
            </span>{" "}
            entries
          </div>
          <div className="flex items-center gap-x-2">
            <p className="text-sm text-muted-foreground">Rows per page</p>
            <Select
              value={`${table.getState().pagination.pageSize}`}
              onValueChange={(value) => {
                table.setPageSize(Number(value))
              }}
            >
              <SelectTrigger
                className="h-8 w-[70px]"
                aria-label="Rows per page"
              >
                <SelectValue
                  placeholder={table.getState().pagination.pageSize}
                />
              </SelectTrigger>
              <SelectContent side="top">
                {[10, 100, 1_000, 10_000, 100_000].map((pageSize) => (
                  <SelectItem key={pageSize} value={`${pageSize}`}>
                    {pageSize}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>

        {table.getPageCount() > 1 && (
          <div className="flex items-center gap-x-6">
            <div className="flex items-center gap-x-1 text-sm text-muted-foreground">
              <span>Page</span>
              <span className="font-medium text-foreground">
                {table.getState().pagination.pageIndex + 1}
              </span>
              <span>of</span>
              <span className="font-medium text-foreground">
                {table.getPageCount()}
              </span>
            </div>

            <div className="flex items-center gap-x-1">
              <Button
                variant="outline"
                size="sm"
                className="h-8 w-8 p-0"
                onClick={() => table.setPageIndex(0)}
                disabled={!table.getCanPreviousPage()}
              >
                <span className="sr-only">Go to first page</span>
                <ChevronsLeft className="h-4 w-4" />
              </Button>
              <Button
                variant="outline"
                size="sm"
                className="h-8 w-8 p-0"
                onClick={() => table.previousPage()}
                disabled={!table.getCanPreviousPage()}
              >
                <span className="sr-only">Go to previous page</span>
                <ChevronLeft className="h-4 w-4" />
              </Button>
              <Button
                variant="outline"
                size="sm"
                className="h-8 w-8 p-0"
                onClick={() => table.nextPage()}
                disabled={!table.getCanNextPage()}
              >
                <span className="sr-only">Go to next page</span>
                <ChevronRight className="h-4 w-4" />
              </Button>
              <Button
                variant="outline"
                size="sm"
                className="h-8 w-8 p-0"
                onClick={() => table.setPageIndex(table.getPageCount() - 1)}
                disabled={!table.getCanNextPage()}
              >
                <span className="sr-only">Go to last page</span>
                <ChevronsRight className="h-4 w-4" />
              </Button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

function Filter<TData, TValue>({ column }: { column: Column<TData, TValue> }) {
  const { filterVariant, serverFilter } = column.columnDef.meta ?? {}

  const columnFilterValue = column.getFilterValue()

  // biome-ignore lint/correctness/useExhaustiveDependencies: matches the official example — recompute when the faceted values change
  const sortedUniqueValues = useMemo(
    () =>
      filterVariant === "range"
        ? []
        : Array.from(column.getFacetedUniqueValues().keys())
            .sort()
            .slice(0, 5000),
    [column.getFacetedUniqueValues(), filterVariant],
  )

  if (serverFilter) {
    return (
      <DebouncedInput
        type="text"
        value={serverFilter.value}
        onChange={(value) => serverFilter.onChange(String(value))}
        placeholder={serverFilter.placeholder ?? "Search..."}
        className={cn(TABLE_FILTER_INPUT_CLASS, "w-36")}
      />
    )
  }

  // TODO: Validate this if block.
  if (filterVariant === "dateRange") {
    const value = (columnFilterValue as DateRangeFilterValue) ?? {}

    const applyFilter = (updatedValue: DateRangeFilterValue) => {
      const cleaned: DateRangeFilterValue = {
        minimumDate: updatedValue.minimumDate || undefined,
        maximumDate: updatedValue.maximumDate || undefined,
        hideBlanks: updatedValue.hideBlanks || undefined,
      }
      column.setFilterValue(
        cleaned.minimumDate || cleaned.maximumDate || cleaned.hideBlanks
          ? cleaned
          : undefined,
      )
    }

    const hideBlanks = value.hideBlanks ?? false

    const setBound = (
      bound: "minimumDate" | "maximumDate",
      date: string,
      time: string,
    ) => {
      applyFilter({
        ...value,
        [bound]: date ? `${date}T${time || "00:00"}` : undefined,
      })
    }

    const bounds = [
      { key: "minimumDate", label: "Minimum" },
      { key: "maximumDate", label: "Maximum" },
    ] as const

    return (
      <div className="flex flex-col gap-1">
        {bounds.map(({ key, label }) => {
          const date = value[key]?.split("T")[0] ?? ""
          const time = value[key]?.split("T")[1] ?? "00:00"
          return (
            <div
              key={key}
              className={cn(
                "border-input dark:bg-input/30 flex h-7 w-52 items-center rounded-md border bg-transparent text-xs",
                "focus-within:border-ring focus-within:ring-ring/50 focus-within:ring-[3px]",
              )}
            >
              <input
                type="date"
                aria-label={`${label} date`}
                value={date}
                onChange={(event) => setBound(key, event.target.value, time)}
                className="min-w-0 flex-1 bg-transparent px-1 outline-none"
              />
              <input
                type="time"
                aria-label={`${label} time`}
                value={time}
                disabled={!date}
                onChange={(event) => setBound(key, date, event.target.value)}
                className="border-input min-w-0 border-l bg-transparent px-1 outline-none disabled:opacity-50"
              />
            </div>
          )
        })}
        <label className="flex items-center gap-1 text-xs text-muted-foreground">
          <input
            type="checkbox"
            checked={hideBlanks}
            onChange={(event) =>
              applyFilter({ ...value, hideBlanks: event.target.checked })
            }
          />
          Hide Blanks
        </label>
      </div>
    )
  }

  if (filterVariant === "range") {
    return (
      <div>
        <div className="flex space-x-2">
          <DebouncedInput
            type="number"
            min={Number(column.getFacetedMinMaxValues()?.[0] ?? "")}
            max={Number(column.getFacetedMinMaxValues()?.[1] ?? "")}
            value={(columnFilterValue as [number, number])?.[0] ?? ""}
            onChange={(value) =>
              column.setFilterValue((old: [number, number]) => [
                value,
                old?.[1],
              ])
            }
            placeholder={`Min ${
              column.getFacetedMinMaxValues()?.[0] !== undefined
                ? `(${column.getFacetedMinMaxValues()?.[0]})`
                : ""
            }`}
            className={cn(TABLE_FILTER_INPUT_CLASS, "w-24")}
          />
          <DebouncedInput
            type="number"
            min={Number(column.getFacetedMinMaxValues()?.[0] ?? "")}
            max={Number(column.getFacetedMinMaxValues()?.[1] ?? "")}
            value={(columnFilterValue as [number, number])?.[1] ?? ""}
            onChange={(value) =>
              column.setFilterValue((old: [number, number]) => [
                old?.[0],
                value,
              ])
            }
            placeholder={`Max ${
              column.getFacetedMinMaxValues()?.[1]
                ? `(${column.getFacetedMinMaxValues()?.[1]})`
                : ""
            }`}
            className={cn(TABLE_FILTER_INPUT_CLASS, "w-24")}
          />
        </div>
        <div className="h-1" />
      </div>
    )
  }

  if (filterVariant === "select") {
    return (
      <select
        onChange={(e) => column.setFilterValue(e.target.value)}
        value={columnFilterValue?.toString()}
        className={cn(TABLE_FILTER_INPUT_CLASS, "rounded border px-1")}
      >
        <option value="">All</option>
        {sortedUniqueValues.map((value) => (
          //dynamically generated select options from faceted values feature
          <option value={value} key={value}>
            {value}
          </option>
        ))}
      </select>
    )
  }

  return (
    <>
      {/* Autocomplete suggestions from faceted values feature */}
      <datalist id={`${column.id}list`}>
        {sortedUniqueValues.map((value: string) => (
          <option value={value} key={value} />
        ))}
      </datalist>
      <DebouncedInput
        type="text"
        value={(columnFilterValue ?? "") as string}
        onChange={(value) => column.setFilterValue(value)}
        placeholder={`Search... (${column.getFacetedUniqueValues().size})`}
        className={cn(TABLE_FILTER_INPUT_CLASS, "w-36")}
        list={`${column.id}list`}
      />
      <div className="h-1" />
    </>
  )
}

// A typical debounced input react component
function DebouncedInput({
  value: initialValue,
  onChange,
  debounce = 500,
  ...props
}: {
  value: string | number
  onChange: (value: string | number) => void
  debounce?: number
} & Omit<React.InputHTMLAttributes<HTMLInputElement>, "onChange">) {
  const [value, setValue] = useState(initialValue)

  useEffect(() => {
    setValue(initialValue)
  }, [initialValue])

  // biome-ignore lint/correctness/useExhaustiveDependencies: matches the official example — only re-fire when the debounced value changes
  useEffect(() => {
    const timeout = setTimeout(() => {
      onChange(value)
    }, debounce)

    return () => clearTimeout(timeout)
  }, [value])

  return (
    <Input
      {...props}
      value={value}
      onChange={(event) => setValue(event.target.value)}
    />
  )
}
