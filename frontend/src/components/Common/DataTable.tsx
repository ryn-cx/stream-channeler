// TODO: Validate
import { keepPreviousData, useQuery } from "@tanstack/react-query"
import { useNavigate, useSearch } from "@tanstack/react-router"
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
  type RowData,
  type SortingState as SortOptionsState,
  type Table as TableInstance,
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
  type LucideIcon,
} from "lucide-react"
import {
  type ReactNode,
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react"

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
import {
  usePersistedJsonState,
  usePersistedState,
} from "@/hooks/usePersistedState"
import { cn } from "@/lib/utils"
import {
  dateRangeFilter,
  datetimeStringToIsoString,
  numberRangeFilter,
} from "./tableFilters"
import {
  TABLE_FILTER_INPUT_CLASS,
  TABLE_HEADER_CELL_CLASS,
} from "./tableStyles"

declare module "@tanstack/react-table" {
  interface ColumnMeta<TData extends RowData, TValue> {
    filterVariant?: "text" | "range" | "select" | "dateRange"
    filterOptions?: { label: string; value: string }[]
    // Whether the API can sort and filter on this column. A column worked out
    // after the rows are read has no column of the database behind it, so a
    // server-side table offers neither on it rather than asking for a column
    // the API will answer 422 to.
    serverBacked?: boolean
    serverFilter?: {
      value: string
      onChange: (value: string) => void
      placeholder?: string
    }
  }
}

// TODO: Validate
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

// TODO: Validate
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

// TODO: Validate
export function DataTable<TData extends { id: string }, TValue>({
  columns,
  data,
  rowClassName,
  storageKey,
  columnVisibility,
  onColumnVisibilityChange,
  serverSide,
}: DataTableProps<TData, TValue>) {
  const isServerSide = !!serverSide
  const processedColumns = useMemo(
    () =>
      columns.map((column) => {
        const processed =
          isServerSide && column.meta?.serverBacked === false
            ? { ...column, enableSorting: false, enableColumnFilter: false }
            : column
        if (processed.meta?.filterVariant === "dateRange") {
          return { ...processed, filterFn: dateRangeFilter }
        }
        if (processed.meta?.filterVariant === "range") {
          return { ...processed, filterFn: numberRangeFilter }
        }
        return processed
      }),
    [columns, isServerSide],
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

// TODO: Validate
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

// TODO: Validate
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
    const [from = "", to = ""] = (columnFilterValue as [string, string]) ?? []

    // Picking a date without a time covers the whole day: the minimum defaults to the
    // start of the day and the maximum to the end of the day.
    // TODO: Validate
    const setBound = (index: 0 | 1, date: string, time: string) => {
      const defaultTime = index === 0 ? "00:00" : "23:59"
      const nextValue = date ? `${date}T${time || defaultTime}` : ""
      column.setFilterValue((previous: [string, string] | undefined) => {
        const next: [string, string] = [
          previous?.[0] ?? "",
          previous?.[1] ?? "",
        ]
        next[index] = nextValue
        return next[0] || next[1] ? next : undefined
      })
    }

    const bounds = [
      { index: 0, label: "Minimum", value: from },
      { index: 1, label: "Maximum", value: to },
    ] as const

    return (
      <div className="flex flex-col gap-1">
        {bounds.map(({ index, label, value }) => {
          const date = value.split("T")[0] ?? ""
          const time = value.split("T")[1] ?? (index === 0 ? "00:00" : "23:59")
          return (
            <div
              key={label}
              className={cn(
                "border-input dark:bg-input/30 flex h-7 w-52 items-center rounded-md border bg-transparent text-xs",
                "focus-within:border-ring focus-within:ring-ring/50 focus-within:ring-[3px]",
              )}
            >
              <input
                type="date"
                aria-label={`${label} date`}
                value={date}
                onChange={(event) => setBound(index, event.target.value, time)}
                className="min-w-0 flex-1 bg-transparent px-1 outline-none"
              />
              <input
                type="time"
                aria-label={`${label} time`}
                value={time}
                disabled={!date}
                onChange={(event) => setBound(index, date, event.target.value)}
                className="border-input min-w-0 border-l bg-transparent px-1 outline-none disabled:opacity-50"
              />
            </div>
          )
        })}
      </div>
    )
  }

  if (filterVariant === "range") {
    const [min, max] = column.getFacetedMinMaxValues() ?? []
    const [minimum = "", maximum = ""] =
      (columnFilterValue as [string, string]) ?? []

    // Merge against the latest filter value (not a render-time snapshot) so the
    // debounced min/max inputs don't clobber each other when their timers race.
    // TODO: Validate
    const setBound = (index: 0 | 1, next: string | number) => {
      column.setFilterValue((previous: [string, string] | undefined) => {
        const value: [string, string] = [
          previous?.[0] ?? "",
          previous?.[1] ?? "",
        ]
        value[index] = String(next)
        return value[0] || value[1] ? value : undefined
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
          value={minimum}
          onChange={(next) => setBound(0, next)}
          placeholder={`Min ${min !== undefined ? `(${min})` : ""}`}
          className={cn(TABLE_FILTER_INPUT_CLASS, "w-24")}
        />
        <DebouncedInput
          type="number"
          {...boundProps}
          value={maximum}
          onChange={(next) => setBound(1, next)}
          placeholder={`Max ${max !== undefined ? `(${max})` : ""}`}
          className={cn(TABLE_FILTER_INPUT_CLASS, "w-24")}
        />
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
// TODO: Validate
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

// TODO: Validate
function columnId<TData>(
  column: ColumnDef<TData, unknown>,
): string | undefined {
  if (column.id) return column.id
  if ("accessorKey" in column) return String(column.accessorKey)
  return undefined
}

// TODO: Validate
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

  const filterOptions = params.filterOptions.map((filter) => {
    if (filterVariants.get(filter.id) === "dateRange") {
      const [rawMinimum = "", rawMaximum = ""] =
        (filter.value as [string, string]) ?? []
      return {
        id: filter.id,
        value: [
          datetimeStringToIsoString(rawMinimum, "minimum"),
          datetimeStringToIsoString(rawMaximum, "maximum"),
        ],
      }
    }
    return filter
  })

  return {
    sortOptions: JSON.stringify(params.sortOptions),
    filterOptions: JSON.stringify(filterOptions),
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

// TODO: Validate
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
  backButton?: ReactNode
}

// TODO: Validate
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
  backButton,
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
          {backButton}
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

export const CANONICAL_TAB = "canonical"

export const MEDIA_TAB = "media"

export type MediaTab = typeof MEDIA_TAB | typeof CANONICAL_TAB

export type MediaSearch = {
  view?: typeof CANONICAL_TAB
}

export type MediaPath =
  | "/plugins"
  | "/sources"
  | "/shows"
  | "/seasons"
  | "/episodes"
  | "/files"

// TODO: Validate
export const validateMediaSearch = (
  search: Record<string, unknown>,
): MediaSearch => ({
  view: search.view === CANONICAL_TAB ? search.view : undefined,
})

const SCOPE_TABS: { value: MediaTab; label: string }[] = [
  { value: MEDIA_TAB, label: "Media" },
  { value: CANONICAL_TAB, label: "Canonical" },
]

// The canonical tab of a media list: the same page, reading the canonical rows
// of the table instead of the non-canonical rows, so it needs its own columns
// and fetcher.
interface CanonicalTab<TCanonical extends { id: string }> {
  columns: ColumnDef<TCanonical>[]
  defaultHidden?: VisibilityState
  fetchTable: (params: MediaPageParams) => Promise<MediaTableResult<TCanonical>>
}

interface MediaListPageProps<
  TData extends { id: string },
  TCanonical extends { id: string },
> {
  title: string
  path: MediaPath
  columns: ColumnDef<TData>[]
  columnVisibilityKey: string
  defaultHidden?: VisibilityState
  emptyIcon: LucideIcon
  headerActions?: ReactNode
  fetchTable: (params: MediaPageParams) => Promise<MediaTableResult<TData>>
  // Left off by the lists that have no canonical counterpart, which drops the tab.
  canonical?: CanonicalTab<TCanonical>
}

// TODO: Validate
export function MediaListPage<
  TData extends { id: string },
  TCanonical extends { id: string } = TData,
>({
  title,
  path,
  columns,
  columnVisibilityKey,
  defaultHidden = {},
  emptyIcon,
  headerActions,
  fetchTable,
  canonical,
}: MediaListPageProps<TData, TCanonical>) {
  const search = useSearch({ strict: false }) as MediaSearch
  const navigate = useNavigate()
  const [rememberedTab, setRememberedTab] = usePersistedState<MediaTab>(
    `media-scope:${path}`,
    MEDIA_TAB,
  )
  const requestedTab: MediaTab = search.view ?? rememberedTab
  const activeTab: MediaTab =
    requestedTab === CANONICAL_TAB && !canonical ? MEDIA_TAB : requestedTab

  useEffect(() => {
    if (search.view && search.view !== rememberedTab) {
      setRememberedTab(search.view)
    }
  }, [search.view, rememberedTab, setRememberedTab])

  // TODO: Validate
  const setTab = (next: MediaTab) => {
    setRememberedTab(next)
    navigate({
      to: path,
      search: next === MEDIA_TAB ? {} : { view: next },
      replace: true,
    })
  }

  const header = (
    <div className="flex flex-wrap items-center gap-3">
      <h1 className="text-2xl font-bold tracking-tight">{title}</h1>
      {canonical && (
        <Tabs
          value={activeTab}
          onValueChange={(value) => setTab(value as MediaTab)}
        >
          <TabsList>
            {SCOPE_TABS.map((tab) => (
              <TabsTrigger key={tab.value} value={tab.value}>
                {tab.label}
              </TabsTrigger>
            ))}
          </TabsList>
        </Tabs>
      )}
    </div>
  )
  const emptyState = (
    <EmptyState
      icon={emptyIcon}
      title={`No ${title.toLowerCase()} found`}
      description="Nothing to show in this category"
    />
  )

  if (canonical && activeTab === CANONICAL_TAB) {
    return (
      <MediaTablePage
        columns={canonical.columns}
        queryKey={["media-table", title, CANONICAL_TAB]}
        fetchTable={canonical.fetchTable}
        columnVisibilityKey={`${columnVisibilityKey}-canonical`}
        defaultHidden={canonical.defaultHidden ?? {}}
        resetKey={CANONICAL_TAB}
        header={header}
        emptyState={emptyState}
      />
    )
  }

  return (
    <MediaTablePage
      columns={columns}
      queryKey={["media-table", title, MEDIA_TAB]}
      fetchTable={fetchTable}
      columnVisibilityKey={columnVisibilityKey}
      defaultHidden={defaultHidden}
      resetKey={MEDIA_TAB}
      headerActions={headerActions}
      header={header}
      emptyState={emptyState}
    />
  )
}
