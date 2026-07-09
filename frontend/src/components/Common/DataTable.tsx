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
  type RowData,
  type SortingState as SortOptionsState,
  type Table as TableInstance,
  useReactTable,
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
import {
  type ReactNode,
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react"

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
  //allows us to define custom properties for our columns
  interface ColumnMeta<TData extends RowData, TValue> {
    filterVariant?: "text" | "range" | "dateRange" | "select"
    filterOptions?: { label: string; value: string }[]
  }
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
  serverSide,
}: DataTableProps<TData, TValue>) {
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
    columns,
    getRowId: (row) => row.id,
    getCoreRowModel: getCoreRowModel(),
    manualPagination: !!serverSide,
    manualSorting: !!serverSide,
    manualFiltering: !!serverSide,
    rowCount: serverSide?.rowCount,
    getSortedRowModel: serverSide ? undefined : getSortedRowModel(),
    getFilteredRowModel: serverSide ? undefined : getFilteredRowModel(), //client-side filtering
    getPaginationRowModel: serverSide ? undefined : getPaginationRowModel(),
    getFacetedRowModel: serverSide ? undefined : getFacetedRowModel(), // client-side faceting
    getFacetedUniqueValues: serverSide ? undefined : getFacetedUniqueValues(), // generate unique values for select filter/autocomplete
    getFacetedMinMaxValues: serverSide ? undefined : getFacetedMinMaxValues(), // generate min/max values for range filter
    onSortingChange: setSortOptions,
    onColumnFiltersChange: handleFilterOptionsChange,
    onPaginationChange: setPagination,
    state: {
      sorting: sortOptions,
      columnFilters: filterOptions,
      pagination,
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
              {[5, 10, 25, 50].map((size) => (
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

function splitDateTime(value: string | undefined): [string, string] {
  const [date = "", time = ""] = (value ?? "").split("T")
  return [date, time]
}

function joinDateTime(date: string, time: string): string {
  return time ? `${date}T${time}` : date
}

function DateTimeRangeInput({
  value,
  label,
  kind,
  onChange,
}: {
  value: string
  label: string
  kind: "minimum" | "maximum"
  onChange: (updater: (old: string) => string) => void
}) {
  const [date, time] = splitDateTime(value)
  // Picking a date without a time defaults to the start of the day for a minimum and
  // the end of the day for a maximum, so the whole day is covered; the user can still
  // refine or clear the time afterwards.
  const defaultTime = kind === "minimum" ? "00:00" : "23:59"
  return (
    <div className="flex space-x-2">
      <DebouncedInput
        type="date"
        value={date}
        onChange={(next) =>
          onChange((old) => {
            const newDate = String(next)
            const existingTime = splitDateTime(old)[1]
            const nextTime = existingTime || (newDate ? defaultTime : "")
            return joinDateTime(newDate, nextTime)
          })
        }
        aria-label={`${label} date`}
        className={cn(TABLE_FILTER_INPUT_CLASS, "w-36")}
      />
      <DebouncedInput
        type="time"
        value={time}
        onChange={(next) =>
          onChange((old) => joinDateTime(splitDateTime(old)[0], String(next)))
        }
        aria-label={`${label} time`}
        className={cn(TABLE_FILTER_INPUT_CLASS, "w-28")}
      />
    </div>
  )
}

function Filter<TData, TValue>({
  column,
  isServerSide,
}: {
  column: Column<TData, TValue>
  isServerSide: boolean
}) {
  const { filterVariant, filterOptions } = column.columnDef.meta ?? {}

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

  if (filterVariant === "range") {
    const [min, max] = column.getFacetedMinMaxValues() ?? []
    return (
      <div>
        <div className="flex space-x-2">
          <DebouncedInput
            type="number"
            min={Number(min ?? "")}
            max={Number(max ?? "")}
            value={(columnFilterValue as [number, number])?.[0] ?? ""}
            onChange={(value) =>
              column.setFilterValue((old: [number, number]) => [
                value,
                old?.[1],
              ])
            }
            placeholder={`Min ${min !== undefined ? `(${min})` : ""}`}
            className={cn(TABLE_FILTER_INPUT_CLASS, "w-24")}
          />
          <DebouncedInput
            type="number"
            min={Number(min ?? "")}
            max={Number(max ?? "")}
            value={(columnFilterValue as [number, number])?.[1] ?? ""}
            onChange={(value) =>
              column.setFilterValue((old: [number, number]) => [
                old?.[0],
                value,
              ])
            }
            placeholder={`Max ${max ? `(${max})` : ""}`}
            className={cn(TABLE_FILTER_INPUT_CLASS, "w-24")}
          />
        </div>
        <div className="h-1" />
      </div>
    )
  }

  if (filterVariant === "dateRange") {
    const [from = "", to = ""] = (columnFilterValue as [string, string]) ?? []
    const updateDateFilter =
      (index: 0 | 1) =>
      (updater: (old: string) => string) =>
        column.setFilterValue((old: [string, string]) => {
          const next: [string, string] = [old?.[0] ?? "", old?.[1] ?? ""]
          next[index] = updater(next[index])
          return next
        })
    return (
      <div>
        <div className="flex flex-col space-y-2">
          <DateTimeRangeInput
            value={from}
            label="From"
            kind="minimum"
            onChange={updateDateFilter(0)}
          />
          <DateTimeRangeInput
            value={to}
            label="To"
            kind="maximum"
            onChange={updateDateFilter(1)}
          />
        </div>
        <div className="h-1" />
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

export interface TablePageParams {
  offset: number
  limit: number
  sortOptions: SortOptionsState
  filterOptions: FilterOptionsState
}

export interface TableResult<TData> {
  data: TData[]
  total_count: number
  filtered_count: number
  is_server_side: boolean
}

interface ServerClientTableProps<TData extends { id: string }> {
  columns: ColumnDef<TData>[]
  queryKey: unknown[]
  fetchTable: (params: TablePageParams) => Promise<TableResult<TData>>
  storageKey?: string
  pendingRows?: TData[]
  rowClassName?: (row: TData) => string | undefined
  emptyState?: ReactNode
  loadingFallback?: ReactNode
}

export function ServerClientTable<TData extends { id: string }>({
  columns,
  queryKey,
  fetchTable,
  storageKey,
  pendingRows = [],
  rowClassName,
  emptyState,
  loadingFallback,
}: ServerClientTableProps<TData>) {
  const [pagination, setPagination] = useState<PaginationState>({
    pageIndex: 0,
    pageSize: 10,
  })
  const [sortOptions, setSortOptions] = useState<SortOptionsState>([])
  const [filterOptions, setFilterOptions] = useState<FilterOptionsState>([])

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

  const isServerSide = tableQuery.data?.is_server_side ?? false
  const rows = tableQuery.data?.data

  if (rows === undefined) {
    return <>{loadingFallback ?? null}</>
  }

  const data = [...pendingRows, ...rows]

  if (!isServerSide && data.length === 0 && emptyState) {
    return <>{emptyState}</>
  }

  return (
    <div
      className={
        tableQuery.isPlaceholderData
          ? "opacity-60 transition-opacity duration-200"
          : undefined
      }
    >
      <DataTable
        columns={columns}
        data={data}
        rowClassName={rowClassName}
        storageKey={storageKey}
        serverSide={
          isServerSide
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
  )
}
