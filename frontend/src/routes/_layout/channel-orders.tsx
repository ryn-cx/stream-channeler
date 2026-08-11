// TODO: Validate
import { keepPreviousData, useQuery } from "@tanstack/react-query"
import { createFileRoute, redirect, useNavigate } from "@tanstack/react-router"
import {
  type ColumnDef,
  type ColumnFiltersState,
  getCoreRowModel,
  type PaginationState,
  type SortingState,
  useReactTable,
  type VisibilityState,
} from "@tanstack/react-table"
import { ListOrdered, Plus } from "lucide-react"
import { useState } from "react"

import { ChannelOrdersService, type RecordScope } from "@/client"
import { CreateChannelOrderDialog } from "@/components/ChannelOrders/CreateChannelOrderDialog"
import { EditOrderConfigDialog } from "@/components/ChannelOrders/EditOrderConfigDialog"
import { OrdersBrowse } from "@/components/ChannelOrders/OrdersBrowse"
import {
  type OrderRow,
  orderColumns,
} from "@/components/ChannelOrders/orderColumns"
import { BrowsePagination } from "@/components/Common/BrowsePagination"
import { ColumnVisibilityButton } from "@/components/Common/ColumnVisibilityButton"
import {
  DataTable,
  type MediaTableResult,
  serializeTableQuery,
} from "@/components/Common/DataTable"
import { EmptyState } from "@/components/Common/EmptyState"
import { type ViewMode, ViewModeTabs } from "@/components/Common/ViewModeTabs"
import { Button } from "@/components/ui/button"
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"
import useAuth, { isLoggedIn } from "@/hooks/useAuth"
import {
  usePersistedJsonState,
  usePersistedState,
} from "@/hooks/usePersistedState"

type Scope = RecordScope

type OrdersSearch = {
  view?: "favorites" | "public" | "all"
}

export const Route = createFileRoute("/_layout/channel-orders")({
  component: OrdersPage,
  beforeLoad: async () => {
    if (!isLoggedIn()) {
      throw redirect({ to: "/" })
    }
  },
  validateSearch: (search: Record<string, unknown>): OrdersSearch => ({
    view:
      search.view === "favorites" ||
      search.view === "public" ||
      search.view === "all"
        ? search.view
        : undefined,
  }),
  head: () => ({
    meta: [{ title: "Orders - Stream Channeler" }],
  }),
})

const emptyStates: Record<Scope, { title: string; description: string }> = {
  owned: {
    title: "You haven't saved any orders yet",
    description:
      "Create one, or save the current sorting from a channel's sorting options.",
  },
  favorites: {
    title: "No favorite orders yet",
    description: "Star an order to keep it here.",
  },
  public: {
    title: "No public orders yet",
    description: "Public orders shared by other users will show up here.",
  },
  all: {
    title: "No orders yet",
    description: "Orders created by any user will show up here.",
  },
}

// Admins read every tab through the admin endpoint, which is the only one that
// carries `score`; everyone else uses the owned and public endpoints.
// TODO: Validate
function useScopedOrders(
  scope: Scope,
  isAdmin: boolean,
  params: {
    offset: number
    limit: number
    sortOptions: SortingState
    filterOptions: ColumnFiltersState
  },
  columns: ColumnDef<OrderRow, unknown>[],
) {
  return useQuery({
    queryKey: [
      "channel-orders",
      scope,
      isAdmin,
      params.offset,
      params.limit,
      params.sortOptions,
      params.filterOptions,
    ],
    queryFn: async (): Promise<MediaTableResult<OrderRow>> =>
      ChannelOrdersService.getChannelOrders({
        scope,
        offset: params.offset,
        limit: params.limit,
        ...serializeTableQuery(params, columns),
      }),
    placeholderData: keepPreviousData,
  })
}

// TODO: Validate
function OrdersTable({
  scope,
  scopeTabs,
  onCreate,
}: {
  scope: Scope
  scopeTabs: React.ReactNode
  onCreate: () => void
}) {
  const { user } = useAuth()
  const isAdmin = user?.is_superuser ?? false
  const [pagination, setPagination] = useState<PaginationState>({
    pageIndex: 0,
    pageSize: 10,
  })
  const [sortOptions, setSortOptions] = useState<SortingState>([])
  const [filterOptions, setFilterOptions] = useState<ColumnFiltersState>([])
  const [editOrder, setEditOrder] = useState<OrderRow | null>(null)
  const [viewMode, setViewMode] = usePersistedState<ViewMode>(
    "orders-list-view",
    "browse",
  )
  const [columnVisibility, setColumnVisibility] =
    usePersistedJsonState<VisibilityState>(
      `orders-${scope}-column-visibility`,
      {},
    )

  // Admins can manage any order, so the row actions follow the viewer's
  // permissions rather than the tab being rendered, matching `orderColumns`.
  const canManage = scope === "owned" || isAdmin
  const columns = orderColumns({
    isOwn: scope === "owned",
    isAdmin,
    onEditConfig: (order) => setEditOrder(order),
  })

  const offset = pagination.pageIndex * pagination.pageSize
  const limit = pagination.pageSize
  const query = useScopedOrders(
    scope,
    isAdmin,
    { offset, limit, sortOptions, filterOptions },
    columns,
  )

  const isServer = query.data?.is_server_side ?? false
  const rows = query.data?.data ?? []
  // The table pages itself when the list is client-side; browse renders plain
  // cards, so it needs the current page sliced out.
  const pageStart = pagination.pageIndex * pagination.pageSize
  const browseRows = isServer
    ? rows
    : rows.slice(pageStart, pageStart + pagination.pageSize)
  const rowCount = isServer ? (query.data?.filtered_count ?? 0) : rows.length

  const table = useReactTable({
    data: rows,
    columns,
    state: { columnVisibility },
    onColumnVisibilityChange: setColumnVisibility,
    getCoreRowModel: getCoreRowModel(),
  })

  const isEmpty = query.data !== undefined && !isServer && rows.length === 0

  return (
    <div>
      <div className="flex flex-wrap items-center justify-between gap-2 px-[4%] pt-4 pb-2">
        <div className="flex flex-wrap items-center gap-3">
          <h1 className="text-2xl font-bold tracking-tight">Orders</h1>
          {scopeTabs}
          <ViewModeTabs value={viewMode} onValueChange={setViewMode} />
        </div>
        <div className="flex shrink-0 items-center gap-2">
          <Button onClick={onCreate}>
            <Plus />
            New Order
          </Button>
          {viewMode === "table" && <ColumnVisibilityButton table={table} />}
        </div>
      </div>

      {isEmpty ? (
        <EmptyState icon={ListOrdered} {...emptyStates[scope]} />
      ) : viewMode === "table" ? (
        <div
          className={
            query.isPlaceholderData
              ? "px-[4%] opacity-60 transition-opacity duration-200"
              : "px-[4%]"
          }
        >
          <DataTable
            columns={columns}
            data={rows}
            storageKey={`orders-${scope}`}
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
                    rowCount: query.data?.filtered_count ?? 0,
                    totalRowCount: query.data?.total_count ?? 0,
                  }
                : undefined
            }
          />
        </div>
      ) : (
        <div
          className={
            query.isPlaceholderData
              ? "opacity-60 transition-opacity duration-200"
              : undefined
          }
        >
          <OrdersBrowse
            orders={browseRows}
            canManage={canManage}
            onEditConfig={(order) => setEditOrder(order)}
          />
          <BrowsePagination
            pagination={pagination}
            onPaginationChange={setPagination}
            rowCount={rowCount}
            itemLabel="Orders"
          />
        </div>
      )}

      {editOrder && (
        <EditOrderConfigDialog
          order={editOrder}
          open
          onOpenChange={(open) => {
            if (!open) setEditOrder(null)
          }}
        />
      )}
    </div>
  )
}

// TODO: Validate
function OrdersPage() {
  const search = Route.useSearch()
  const navigate = useNavigate()
  const { user } = useAuth()
  const isAdmin = user?.is_superuser ?? false
  const scope: Scope = search.view ?? "owned"
  const [createOpen, setCreateOpen] = useState(false)

  // TODO: Validate
  const setScope = (next: Scope) => {
    navigate({
      to: "/channel-orders",
      search: next === "owned" ? {} : { view: next },
      replace: true,
    })
  }

  const scopeTabs = (
    <Tabs value={scope} onValueChange={(value) => setScope(value as Scope)}>
      <TabsList>
        <TabsTrigger value="owned">Owned</TabsTrigger>
        <TabsTrigger value="favorites">Favorites</TabsTrigger>
        <TabsTrigger value="public">Public</TabsTrigger>
        {isAdmin && <TabsTrigger value="all">All</TabsTrigger>}
      </TabsList>
    </Tabs>
  )

  return (
    <div className="flex flex-col gap-6">
      <OrdersTable
        key={scope}
        scope={scope === "all" && !isAdmin ? "public" : scope}
        scopeTabs={scopeTabs}
        onCreate={() => setCreateOpen(true)}
      />

      {createOpen && (
        <CreateChannelOrderDialog
          open={createOpen}
          onOpenChange={setCreateOpen}
        />
      )}
    </div>
  )
}
