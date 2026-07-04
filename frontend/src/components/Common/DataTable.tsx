// TODO: Validate
import { keepPreviousData, useQuery } from "@tanstack/react-query"
import {
  type Column,
  type ColumnDef,
  type ColumnFiltersState as FilterOptionsState,
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
  type SortingState as SortOptionsState,
  type Table as TableInstance,
  useReactTable,
  type VisibilityState,
} from "@tanstack/react-table"
import {
  ArrowDown,
  ArrowLeft,
  ArrowUp,
  ChevronLeft,
  ChevronRight,
  ChevronsLeft,
  ChevronsRight,
  ChevronsUpDown,
  type LucideIcon,
} from "lucide-react"
import {
  type ReactNode,
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react"

import type { MediaOwner } from "@/client"
import { ColumnVisibilityButton } from "@/components/Common/ColumnVisibilityButton"
import { DataTableSkeleton } from "@/components/Common/DataTableSkeleton"
import { EmptyState } from "@/components/Common/EmptyState"
import { MediaSubNav } from "@/components/Media/MediaSubNav"
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
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"
import useAuth from "@/hooks/useAuth"
import {
  usePersistedJsonState,
  usePersistedState,
} from "@/hooks/usePersistedState"
import { cn } from "@/lib/utils"
import {
  TABLE_FILTER_INPUT_CLASS,
  TABLE_HEADER_CELL_CLASS,
} from "./tableStyles"

declare module "@tanstack/react-table" {
  interface ColumnMeta<TData extends RowData, TValue> {
    filterVariant?: "text" | "range" | "select" | "dateRange"
    filterOptions?: { label: string; value: string }[]
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

function parseNumberBound(value: unknown): number | null {
  if (value === "" || value === null || value === undefined) return null
  const parsed = Number(value)
  return Number.isNaN(parsed) ? null : parsed
}

interface NumberRangeFilterValue {
  minimum?: string
  maximum?: string
  hideBlanks?: boolean
}

function numberRangeFilterFn<TData>(
  row: Row<TData>,
  columnId: string,
  filterValue: NumberRangeFilterValue,
): boolean {
  const rawValue = row.getValue(columnId) as number | null | undefined
  const { minimum, maximum, hideBlanks } = filterValue ?? {}
  const minimumBound = parseNumberBound(minimum)
  const maximumBound = parseNumberBound(maximum)

  // Blank values should always be shown unless explicitly hidden.
  if (rawValue === null || rawValue === undefined) return !hideBlanks

  if (minimumBound !== null && rawValue < minimumBound) return false
  if (maximumBound !== null && rawValue > maximumBound) return false
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

interface ServerSideTableState {
  pagination: PaginationState
  sortOptions: SortOptionsState
  filterOptions: FilterOptionsState
  onPaginationChange: OnChangeFn<PaginationState>
  onSortOptionsChange: OnChangeFn<SortOptionsState>
  onFilterOptionsChange: OnChangeFn<FilterOptionsState>
  rowCount: number
  totalRowCount: number
}

interface DataTableProps<TData extends { id: string }, TValue> {
  columns: ColumnDef<TData, TValue>[]
  data: TData[]
  rowClassName?: (row: TData) => string | undefined
  storageKey?: string
  columnVisibility?: VisibilityState
  onColumnVisibilityChange?: OnChangeFn<VisibilityState>
  serverSide?: ServerSideTableState
}

function useTableState(
  serverSide: ServerSideTableState | undefined,
  storageKey: string | undefined,
) {
  const [clientSortOptions, setClientSortOptions] =
    usePersistentState<SortOptionsState>(
      storageKey && `${storageKey}:sortOptions`,
      [],
    )
  const [clientFilterOptions, setClientFilterOptions] =
    usePersistentState<FilterOptionsState>(
      storageKey && `${storageKey}:filterOptions`,
      [],
    )
  const [clientPagination, setClientPagination] =
    usePersistentState<PaginationState>(
      storageKey && `${storageKey}:pagination`,
      {
        pageIndex: 0,
        pageSize: 10,
      },
    )

  if (serverSide) {
    return {
      sortOptions: serverSide.sortOptions,
      filterOptions: serverSide.filterOptions,
      pagination: serverSide.pagination,
      setSortOptions: serverSide.onSortOptionsChange,
      setFilterOptions: serverSide.onFilterOptionsChange,
      setPagination: serverSide.onPaginationChange,
    }
  }
  return {
    sortOptions: clientSortOptions,
    filterOptions: clientFilterOptions,
    pagination: clientPagination,
    setSortOptions: setClientSortOptions,
    setFilterOptions: setClientFilterOptions,
    setPagination: setClientPagination,
  }
}

export function DataTable<TData extends { id: string }, TValue>({
  columns,
  data,
  rowClassName,
  storageKey,
  columnVisibility,
  onColumnVisibilityChange,
  serverSide,
}: DataTableProps<TData, TValue>) {
  const processedColumns = useMemo(
    () =>
      columns.map((column) => {
        if (column.meta?.filterVariant === "dateRange") {
          return { ...column, filterFn: dateRangeFilterFn }
        }
        if (column.meta?.filterVariant === "range") {
          return { ...column, filterFn: numberRangeFilterFn }
        }
        return column
      }),
    [columns],
  )

  const {
    sortOptions,
    filterOptions,
    pagination,
    setSortOptions,
    setFilterOptions,
    setPagination,
  } = useTableState(serverSide, storageKey)

  const handleFilterOptionsChange: OnChangeFn<FilterOptionsState> = useCallback(
    (updater) => {
      setFilterOptions((last) => {
        const next = typeof updater === "function" ? updater(last) : updater
        if (JSON.stringify(next) !== JSON.stringify(last)) {
          setPagination((p) => ({ ...p, pageIndex: 0 }))
        }
        return next
      })
    },
    [setFilterOptions, setPagination],
  )

  const table = useReactTable({
    data,
    columns: processedColumns,
    getRowId: (row) => row.id,
    getCoreRowModel: getCoreRowModel(),
    manualPagination: !!serverSide,
    manualSorting: !!serverSide,
    manualFiltering: !!serverSide,
    rowCount: serverSide?.rowCount,
    getSortedRowModel: serverSide ? undefined : getSortedRowModel(),
    getFilteredRowModel: serverSide ? undefined : getFilteredRowModel(),
    getPaginationRowModel: serverSide ? undefined : getPaginationRowModel(),
    getFacetedRowModel: serverSide ? undefined : getFacetedRowModel(),
    getFacetedUniqueValues: serverSide ? undefined : getFacetedUniqueValues(),
    getFacetedMinMaxValues: serverSide ? undefined : getFacetedMinMaxValues(),
    onSortingChange: setSortOptions,
    onColumnFiltersChange: handleFilterOptionsChange,
    onPaginationChange: setPagination,
    onColumnVisibilityChange,
    state: {
      sorting: sortOptions,
      columnFilters: filterOptions,
      pagination,
      columnVisibility,
    },
    autoResetPageIndex: false,
  })

  const filteredRows = serverSide
    ? serverSide.rowCount
    : table.getFilteredRowModel().rows.length
  const totalRows = serverSide
    ? serverSide.totalRowCount
    : table.getCoreRowModel().rows.length
  const isFiltered = filteredRows !== totalRows

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
                          <Filter column={column} isServerSide={!!serverSide} />
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

      <TablePagination
        table={table}
        filteredRows={filteredRows}
        totalRows={totalRows}
        isFiltered={isFiltered}
      />
    </div>
  )
}

function TablePagination<TData>({
  table,
  filteredRows,
  totalRows,
  isFiltered,
}: {
  table: TableInstance<TData>
  filteredRows: number
  totalRows: number
  isFiltered: boolean
}) {
  const { pageIndex, pageSize } = table.getState().pagination

  return (
    <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 p-4 border-t bg-muted/20">
      <div className="flex flex-col sm:flex-row sm:items-center gap-4">
        <div className="text-sm text-muted-foreground">
          Showing {pageIndex * pageSize + 1} to{" "}
          {Math.min((pageIndex + 1) * pageSize, filteredRows)} of{" "}
          <span className="font-medium text-foreground">{filteredRows}</span>{" "}
          entries
          {isFiltered && (
            <>
              {" "}
              (filtered from{" "}
              <span className="font-medium text-foreground">{totalRows}</span>{" "}
              total)
            </>
          )}
        </div>
        <div className="flex items-center gap-x-2">
          <p className="text-sm text-muted-foreground">Rows per page</p>
          <Select
            value={`${pageSize}`}
            onValueChange={(value) => table.setPageSize(Number(value))}
          >
            <SelectTrigger className="h-8 w-[70px]" aria-label="Rows per page">
              <SelectValue placeholder={pageSize} />
            </SelectTrigger>
            <SelectContent side="top">
              {[10, 100, 1_000].map((size) => (
                <SelectItem key={size} value={`${size}`}>
                  {size}
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
            <span className="font-medium text-foreground">{pageIndex + 1}</span>
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
  )
}

const SELECT_ALL_VALUE = "__all__"

function Filter<TData, TValue>({
  column,
  isServerSide,
}: {
  column: Column<TData, TValue>
  isServerSide: boolean
}) {
  const { filterVariant, filterOptions, serverFilter } =
    column.columnDef.meta ?? {}

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
    const [min, max] = column.getFacetedMinMaxValues() ?? []
    const value = (columnFilterValue as NumberRangeFilterValue) ?? {}

    // Merge against the latest filter value (not a render-time snapshot) so the
    // debounced min/max inputs don't clobber each other when their timers race.
    const applyFilter = (patch: NumberRangeFilterValue) => {
      column.setFilterValue((previous: NumberRangeFilterValue | undefined) => {
        const merged = { ...(previous ?? {}), ...patch }
        const cleaned: NumberRangeFilterValue = {
          minimum: merged.minimum || undefined,
          maximum: merged.maximum || undefined,
          hideBlanks: merged.hideBlanks || undefined,
        }
        return cleaned.minimum || cleaned.maximum || cleaned.hideBlanks
          ? cleaned
          : undefined
      })
    }

    const boundProps = {
      ...(min !== undefined ? { min: Number(min) } : {}),
      ...(max !== undefined ? { max: Number(max) } : {}),
    }

    return (
      <div className="flex flex-col gap-1">
        <DebouncedInput
          type="number"
          {...boundProps}
          value={value.minimum ?? ""}
          onChange={(next) => applyFilter({ minimum: String(next) })}
          placeholder={`Min ${min !== undefined ? `(${min})` : ""}`}
          className={cn(TABLE_FILTER_INPUT_CLASS, "w-24")}
        />
        <DebouncedInput
          type="number"
          {...boundProps}
          value={value.maximum ?? ""}
          onChange={(next) => applyFilter({ maximum: String(next) })}
          placeholder={`Max ${max !== undefined ? `(${max})` : ""}`}
          className={cn(TABLE_FILTER_INPUT_CLASS, "w-24")}
        />
        <label className="flex items-center gap-1 text-xs text-muted-foreground">
          <input
            type="checkbox"
            checked={value.hideBlanks ?? false}
            onChange={(event) =>
              applyFilter({ hideBlanks: event.target.checked })
            }
          />
          Hide Blanks
        </label>
      </div>
    )
  }

  if (filterVariant === "select") {
    const options =
      filterOptions ??
      sortedUniqueValues.map((value) => ({
        label: String(value),
        value: String(value),
      }))
    return (
      <Select
        value={columnFilterValue ? String(columnFilterValue) : SELECT_ALL_VALUE}
        onValueChange={(value) =>
          column.setFilterValue(value === SELECT_ALL_VALUE ? undefined : value)
        }
      >
        <SelectTrigger
          className={cn(TABLE_FILTER_INPUT_CLASS, "h-8 w-36")}
          aria-label="Filter"
        >
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value={SELECT_ALL_VALUE}>All</SelectItem>
          {options.map(({ label, value }) => (
            <SelectItem key={value} value={value}>
              {label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    )
  }

  return (
    <>
      <datalist id={`${column.id}list`}>
        {sortedUniqueValues.map((value: string) => (
          <option value={value} key={value} />
        ))}
      </datalist>
      <DebouncedInput
        type="text"
        value={(columnFilterValue ?? "") as string}
        onChange={(value) => column.setFilterValue(value)}
        placeholder={
          isServerSide
            ? "Search..."
            : `Search... (${column.getFacetedUniqueValues().size})`
        }
        className={cn(TABLE_FILTER_INPUT_CLASS, "w-36")}
        list={`${column.id}list`}
      />
      <div className="h-1" />
    </>
  )
}

// Copied from https://tanstack.com/table/v8/docs/framework/react/examples/filters
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

  useEffect(() => {
    const timeout = setTimeout(() => {
      onChange(value)
    }, debounce)

    return () => clearTimeout(timeout)
  }, [value, debounce, onChange])

  return (
    <Input
      {...props}
      value={value}
      onChange={(event) => setValue(event.target.value)}
    />
  )
}

export interface MediaPageParams {
  offset: number
  limit: number
  sortOptions: SortOptionsState
  filterOptions: FilterOptionsState
}

export interface MediaTableResult<TData> {
  data: TData[]
  total_count: number
  filtered_count: number
  is_server_side: boolean
}

interface NumberFilterOption {
  id: string
  value: {
    minimum: number | null
    maximum: number | null
    hideBlanks: boolean
  }
}

function columnId<TData>(
  column: ColumnDef<TData, unknown>,
): string | undefined {
  if (column.id) return column.id
  if ("accessorKey" in column) return String(column.accessorKey)
  return undefined
}

export function serializeTableQuery<TData>(
  params: MediaPageParams,
  columns: ColumnDef<TData, unknown>[],
) {
  const filterVariants = new Map<string, string>()
  for (const column of columns) {
    const id = columnId(column)
    if (id && column.meta?.filterVariant) {
      filterVariants.set(id, column.meta.filterVariant)
    }
  }

  const stringFilters: FilterOptionsState = []
  const dateFilters: FilterOptionsState = []
  const numberFilters: NumberFilterOption[] = []
  for (const filter of params.filterOptions) {
    const variant = filterVariants.get(filter.id)
    if (variant === "dateRange") {
      dateFilters.push(filter)
    } else if (variant === "range") {
      const { minimum, maximum, hideBlanks } =
        (filter.value as NumberRangeFilterValue) ?? {}
      numberFilters.push({
        id: filter.id,
        value: {
          minimum: parseNumberBound(minimum),
          maximum: parseNumberBound(maximum),
          hideBlanks: hideBlanks ?? false,
        },
      })
    } else {
      stringFilters.push(filter)
    }
  }
  return {
    sortOptions: JSON.stringify(params.sortOptions),
    filterOptions: JSON.stringify(stringFilters),
    dateFilterOptions: JSON.stringify(dateFilters),
    numberFilterOptions: JSON.stringify(numberFilters),
  }
}

interface MediaTablePageProps<TData extends { id: string }> {
  columns: ColumnDef<TData>[]
  queryKey: unknown[]
  fetchTable: (params: MediaPageParams) => Promise<MediaTableResult<TData>>
  columnVisibilityKey: string
  defaultHidden?: VisibilityState
  header: ReactNode
  headerActions?: ReactNode
  emptyState: ReactNode
  resetKey?: unknown
}

export function MediaTablePage<TData extends { id: string }>({
  columns,
  queryKey,
  fetchTable,
  columnVisibilityKey,
  defaultHidden = {},
  header,
  headerActions,
  emptyState,
  resetKey,
}: MediaTablePageProps<TData>) {
  const [pagination, setPagination] = useState<PaginationState>({
    pageIndex: 0,
    pageSize: 10,
  })
  const [sortOptions, setSortOptions] = useState<SortOptionsState>([])
  const [filterOptions, setFilterOptions] = useState<FilterOptionsState>([])

  // biome-ignore lint/correctness/useExhaustiveDependencies: reset only on resetKey change
  useEffect(() => {
    setPagination((previous) => ({ ...previous, pageIndex: 0 }))
  }, [resetKey])

  const tableQuery = useQuery({
    queryKey: [...queryKey, pagination, sortOptions, filterOptions],
    queryFn: () =>
      fetchTable({
        offset: pagination.pageIndex * pagination.pageSize,
        limit: pagination.pageSize,
        sortOptions,
        filterOptions,
      }),
    placeholderData: keepPreviousData,
  })

  const [columnVisibility, setColumnVisibility] =
    usePersistedJsonState<VisibilityState>(columnVisibilityKey, defaultHidden)

  const isServer = tableQuery.data?.is_server_side ?? false
  const tableData = tableQuery.data?.data

  const table = useReactTable({
    data: tableData ?? [],
    columns,
    state: { columnVisibility },
    onColumnVisibilityChange: setColumnVisibility,
    getCoreRowModel: getCoreRowModel(),
  })

  const isLoading = tableData === undefined
  const isEmpty = !isServer && (tableData?.length ?? 0) === 0

  return (
    <div className="flex flex-col gap-6">
      <MediaSubNav />
      <div
        className={
          tableQuery.isPlaceholderData
            ? "opacity-60 transition-opacity duration-200"
            : undefined
        }
      >
        <div className="flex flex-wrap items-center justify-between gap-2 px-[4%] pt-4 pb-2">
          {header}
          <div className="flex flex-wrap items-center gap-2">
            {headerActions}
            <ColumnVisibilityButton table={table} />
          </div>
        </div>
        {isLoading ? (
          <div className="px-[4%]">
            <DataTableSkeleton table={table} />
          </div>
        ) : isEmpty ? (
          emptyState
        ) : (
          <div className="px-[4%]">
            <DataTable
              columns={columns}
              data={tableData ?? []}
              columnVisibility={columnVisibility}
              onColumnVisibilityChange={setColumnVisibility}
              serverSide={
                isServer
                  ? {
                      pagination,
                      sortOptions,
                      filterOptions,
                      onPaginationChange: setPagination,
                      onSortOptionsChange: setSortOptions,
                      onFilterOptionsChange: setFilterOptions,
                      rowCount: tableQuery.data?.filtered_count ?? 0,
                      totalRowCount: tableQuery.data?.total_count ?? 0,
                    }
                  : undefined
              }
            />
          </div>
        )}
      </div>
    </div>
  )
}

interface DetailTablePageProps<TData extends { id: string }> {
  title: ReactNode
  columns: ColumnDef<TData>[]
  queryKey: unknown[]
  fetchTable: (params: MediaPageParams) => Promise<MediaTableResult<TData>>
  columnVisibilityKey: string
  defaultHidden?: VisibilityState
  emptyIcon: LucideIcon
  emptyTitle: string
  emptyDescription: string
  headerActions?: ReactNode
}

export function DetailTablePage<TData extends { id: string }>({
  title,
  columns,
  queryKey,
  fetchTable,
  columnVisibilityKey,
  defaultHidden = { key: false, id: false },
  emptyIcon,
  emptyTitle,
  emptyDescription,
  headerActions,
}: DetailTablePageProps<TData>) {
  return (
    <MediaTablePage
      columns={columns}
      queryKey={queryKey}
      fetchTable={fetchTable}
      columnVisibilityKey={columnVisibilityKey}
      defaultHidden={defaultHidden}
      headerActions={headerActions}
      header={
        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="icon"
            onClick={() => window.history.back()}
          >
            <ArrowLeft />
          </Button>
          {title}
        </div>
      }
      emptyState={
        <EmptyState
          icon={emptyIcon}
          title={emptyTitle}
          description={emptyDescription}
        />
      }
    />
  )
}

export type OwnerView = MediaOwner | undefined
type OwnerTab = "" | MediaOwner

interface MediaListPageProps<TData extends { id: string }> {
  title: string
  // Either a static column set, or a builder that receives the active owner tab
  // (so columns can vary per tab, e.g. admin-only shortcuts on "Official").
  columns: ColumnDef<TData>[] | ((owner: OwnerView) => ColumnDef<TData>[])
  columnVisibilityKey: string
  defaultHidden?: VisibilityState
  emptyIcon: LucideIcon
  headerActions?: (owner: OwnerView) => ReactNode
  fetchTable: (
    owner: OwnerView,
    params: MediaPageParams,
  ) => Promise<MediaTableResult<TData>>
}

export function MediaListPage<TData extends { id: string }>({
  title,
  columns,
  columnVisibilityKey,
  defaultHidden = {},
  emptyIcon,
  headerActions,
  fetchTable,
}: MediaListPageProps<TData>) {
  const { user } = useAuth()
  const isAdmin = user?.is_superuser ?? false
  const [ownerTab, setOwnerTab] = usePersistedState<OwnerTab>(
    "media-owner-view-v2",
    "",
  )
  const ownerFilter: OwnerView =
    isAdmin && ownerTab !== "" ? ownerTab : undefined

  const resolvedColumns = useMemo(
    () => (typeof columns === "function" ? columns(ownerFilter) : columns),
    [columns, ownerFilter],
  )

  return (
    <MediaTablePage
      columns={resolvedColumns}
      queryKey={["media-table", title, ownerFilter]}
      fetchTable={(params) => fetchTable(ownerFilter, params)}
      columnVisibilityKey={columnVisibilityKey}
      defaultHidden={defaultHidden}
      resetKey={ownerFilter}
      headerActions={headerActions?.(ownerFilter)}
      header={
        <div className="flex flex-wrap items-center gap-3">
          <h1 className="text-2xl font-bold tracking-tight">{title}</h1>
          {isAdmin && (
            <Tabs
              value={ownerTab}
              onValueChange={(value) => setOwnerTab(value as OwnerTab)}
            >
              <TabsList>
                {/* I think it's funny that ever option starts with O. */}
                <TabsTrigger value="">Owned</TabsTrigger>
                <TabsTrigger value="official">Official</TabsTrigger>
                <TabsTrigger value="others">Other Users</TabsTrigger>
              </TabsList>
            </Tabs>
          )}
        </div>
      }
      emptyState={
        <EmptyState
          icon={emptyIcon}
          title={`No ${title.toLowerCase()} found`}
          description="Nothing to show in this category"
        />
      }
    />
  )
}
