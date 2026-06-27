// TODO: Validate
import { keepPreviousData, useQuery } from "@tanstack/react-query"
import type {
  ColumnDef,
  ColumnFiltersState,
  PaginationState,
  SortingState,
  VisibilityState,
} from "@tanstack/react-table"
import { getCoreRowModel, useReactTable } from "@tanstack/react-table"
import type { LucideIcon } from "lucide-react"
import { type ReactNode, useEffect, useState } from "react"

import type { MediaOwner } from "@/client"
import { ColumnVisibilityButton } from "@/components/Common/ColumnVisibilityButton"
import { DataTable } from "@/components/Common/DataTable"
import { DataTableSkeleton } from "@/components/Common/DataTableSkeleton"
import { EmptyState } from "@/components/Common/EmptyState"
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"
import useAuth from "@/hooks/useAuth"
import {
  usePersistedJsonState,
  usePersistedState,
} from "@/hooks/usePersistedState"
import { MediaSubNav } from "./MediaSubNav"

// Admins can browse media by owner; everyone else only ever sees their own.
// Own content is an unset owner (`undefined`), so no `owner` is sent to the API.
export type OwnerView = MediaOwner | undefined
// Tab selector value; "" is the own-content tab and maps to an unset `OwnerView`.
type OwnerTab = "" | MediaOwner

export interface MediaPageParams {
  offset: number
  limit: number
  sorting: SortingState
  columnFilters: ColumnFiltersState
}

export interface MediaTableResult<TData> {
  data: TData[]
  /** Filtered total when server-side, otherwise the full row count. */
  count: number
  /** Whether the backend wants the table paginated/sorted/filtered server-side. */
  server_side: boolean
}

interface MediaListPageProps<TData extends { id: string }> {
  title: string
  columns: ColumnDef<TData>[]
  /** localStorage key for column visibility (shared with the detail page). */
  columnVisibilityKey: string
  defaultHidden?: VisibilityState
  emptyIcon: LucideIcon
  /** Extra header controls (e.g. an "add" button), rendered per owner view. */
  headerActions?: (owner: OwnerView) => ReactNode
  /**
   * One request that returns either every row (`server_side: false`) or a single
   * filtered + sorted page (`server_side: true`). The backend decides from the owner
   * view's total size, so no separate count request is needed.
   */
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
  // Shared across all media types so the chosen filter sticks while navigating.
  // Key bumped to v2 so any previously stored "mine" value is discarded; the own
  // content tab is "" and maps to an unset owner.
  const [ownerTab, setOwnerTab] = usePersistedState<OwnerTab>(
    "media-owner-view-v2",
    "",
  )
  const ownerFilter: OwnerView =
    isAdmin && ownerTab !== "" ? ownerTab : undefined

  // Table state. Only wired to the table when the backend returns `server_side`;
  // otherwise the DataTable owns its own state and this stays at the initial page,
  // so the query below runs once per owner view.
  const [pagination, setPagination] = useState<PaginationState>({
    pageIndex: 0,
    pageSize: 10,
  })
  const [sorting, setSorting] = useState<SortingState>([])
  const [columnFilters, setColumnFilters] = useState<ColumnFiltersState>([])

  // Reset to the first page when switching owner views so the offset stays valid.
  // biome-ignore lint/correctness/useExhaustiveDependencies: reset only on owner change
  useEffect(() => {
    setPagination((previous) => ({ ...previous, pageIndex: 0 }))
  }, [ownerFilter])

  const tableQuery = useQuery({
    queryKey: [
      "media-table",
      title,
      ownerFilter,
      pagination,
      sorting,
      columnFilters,
    ],
    queryFn: () =>
      fetchTable(ownerFilter, {
        offset: pagination.pageIndex * pagination.pageSize,
        limit: pagination.pageSize,
        sorting,
        columnFilters,
      }),
    placeholderData: keepPreviousData,
  })

  const [columnVisibility, setColumnVisibility] =
    usePersistedJsonState<VisibilityState>(columnVisibilityKey, defaultHidden)

  const isServer = tableQuery.data?.server_side ?? false
  const tableData = tableQuery.data?.data

  const table = useReactTable({
    data: tableData ?? [],
    columns,
    state: {
      columnVisibility,
    },
    onColumnVisibilityChange: setColumnVisibility,
    getCoreRowModel: getCoreRowModel(),
  })

  const isLoading = tableData === undefined
  // In server mode the page may be empty while filters are active, so never show
  // the empty state there — the table keeps its filter inputs and a "no results"
  // row. Server mode only engages above the threshold, so the view is never truly
  // empty.
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
          <div className="flex flex-wrap items-center gap-3">
            <h1 className="text-2xl font-bold tracking-tight">{title}</h1>
            {isAdmin && (
              <Tabs
                value={ownerTab}
                onValueChange={(value) => setOwnerTab(value as OwnerTab)}
              >
                <TabsList>
                  <TabsTrigger value="">My Media</TabsTrigger>
                  <TabsTrigger value="official">Official</TabsTrigger>
                  <TabsTrigger value="others">Other Users</TabsTrigger>
                </TabsList>
              </Tabs>
            )}
          </div>
          <div className="flex flex-wrap items-center gap-2">
            {headerActions?.(ownerFilter)}
            <ColumnVisibilityButton table={table} />
          </div>
        </div>
        {isLoading ? (
          <div className="px-[4%]">
            <DataTableSkeleton table={table} />
          </div>
        ) : isEmpty ? (
          <EmptyState
            icon={emptyIcon}
            title={`No ${title.toLowerCase()} found`}
            description="Nothing to show in this category"
          />
        ) : (
          <div className="px-[4%]">
            <DataTable
              columns={columns}
              data={tableData ?? []}
              columnVisibility={columnVisibility}
              onColumnVisibilityChange={setColumnVisibility}
              manual={
                isServer
                  ? {
                      pagination,
                      sorting,
                      columnFilters,
                      onPaginationChange: setPagination,
                      onSortingChange: setSorting,
                      onColumnFiltersChange: setColumnFilters,
                      rowCount: tableQuery.data?.count ?? 0,
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
