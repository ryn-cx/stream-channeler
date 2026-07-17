// TODO: Validate
import { createFileRoute, useNavigate } from "@tanstack/react-router"
import type {
  ColumnFiltersState,
  PaginationState,
  SortingState,
  VisibilityState,
} from "@tanstack/react-table"
import { getCoreRowModel, useReactTable } from "@tanstack/react-table"
import { LayoutGrid, Table as TableIcon, Tv } from "lucide-react"
import { type ReactNode, useMemo, useState } from "react"
import AddChannel from "@/components/Channels/ChannelList/AddChannel"
import { AllChannelsView } from "@/components/Channels/ChannelList/AllChannelsView"
import {
  BrowsePagination,
  DEFAULT_BROWSE_PAGE_SIZE,
  MAX_BROWSE_PAGE_SIZE,
} from "@/components/Channels/ChannelList/BrowsePagination"
import { BulkImport } from "@/components/Channels/ChannelList/BulkImport"
import {
  ChannelsBrowse,
  sortOwnedChannels,
} from "@/components/Channels/ChannelList/ChannelsBrowse"
import { ChannelsHeader } from "@/components/Channels/ChannelList/ChannelsHeader"
import { ownedChannelColumns } from "@/components/Channels/ChannelList/columns"
import { PublicChannelsView } from "@/components/Channels/ChannelList/PublicChannelsView"
import { useScopedChannels } from "@/components/Channels/ChannelList/useScopedChannels"
import { ColumnVisibilityButton } from "@/components/Common/ColumnVisibilityButton"
import { DataTable } from "@/components/Common/DataTable"
import { EmptyState } from "@/components/Common/EmptyState"
import PendingChannelList from "@/components/Pending/PendingChannelList"
import { Button } from "@/components/ui/button"
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"
import useAuth, { isLoggedIn } from "@/hooks/useAuth"
import {
  usePersistedJsonState,
  usePersistedState,
} from "@/hooks/usePersistedState"

type Scope = "mine" | "public" | "all"

type ChannelsSearch = {
  view?: "public" | "all"
}

export const Route = createFileRoute("/_layout/channels/")({
  component: Channels,
  validateSearch: (search: Record<string, unknown>): ChannelsSearch => ({
    view:
      search.view === "public" || search.view === "all"
        ? search.view
        : undefined,
  }),
  head: () => ({
    meta: [
      {
        title: "Channels - Stream Channeler",
      },
    ],
  }),
})

type ViewMode = "table" | "browse"

function MyChannels({ scopeTabs }: { scopeTabs: ReactNode }) {
  const { user } = useAuth()
  const isAdmin = user?.is_superuser ?? false
  const [viewMode, setViewMode] = usePersistedState<ViewMode>(
    "channels-list-view",
    "browse",
  )
  const [columnVisibility, setColumnVisibility] =
    usePersistedJsonState<VisibilityState>("channels-column-visibility", {
      id: false,
    })
  const [pagination, setPagination] = useState<PaginationState>({
    pageIndex: 0,
    pageSize: DEFAULT_BROWSE_PAGE_SIZE,
  })
  const [sortOptions, setSortOptions] = useState<SortingState>([])
  const [filterOptions, setFilterOptions] = useState<ColumnFiltersState>([])

  const columns = ownedChannelColumns(isAdmin)
  const query = useScopedChannels(
    "mine",
    isAdmin,
    {
      offset: pagination.pageIndex * pagination.pageSize,
      limit: pagination.pageSize,
      sortOptions,
      filterOptions,
    },
    columns,
  )

  const isServer = query.data?.is_server_side ?? false
  const tableData = query.data?.data ?? []
  const pageStart = pagination.pageIndex * pagination.pageSize
  // The server already returns browse's page in its own order; only a
  // client-side list needs sorting by channel number and slicing here.
  const ordered = useMemo(
    () => (isServer ? tableData : sortOwnedChannels(tableData)),
    [isServer, tableData],
  )
  const pageChannels = isServer
    ? ordered
    : ordered.slice(pageStart, pageStart + pagination.pageSize)
  const rowCount = isServer ? (query.data?.filtered_count ?? 0) : ordered.length

  const table = useReactTable({
    data: tableData,
    columns,
    state: { columnVisibility },
    onColumnVisibilityChange: setColumnVisibility,
    getCoreRowModel: getCoreRowModel(),
  })

  if (!query.data) {
    return (
      <>
        <ChannelsHeader scopeTabs={scopeTabs} />
        <PendingChannelList />
      </>
    )
  }

  return (
    <div
      className={
        query.isPlaceholderData
          ? "opacity-60 transition-opacity duration-200"
          : undefined
      }
    >
      <ChannelsHeader scopeTabs={scopeTabs}>
        {viewMode === "browse" ? (
          <Button
            variant="outline"
            onClick={() => setViewMode("table")}
            title="Switch to table view"
          >
            <TableIcon />
            Table
          </Button>
        ) : (
          <Button
            variant="outline"
            onClick={() => {
              setPagination((current) => ({
                pageIndex: 0,
                pageSize: Math.min(current.pageSize, MAX_BROWSE_PAGE_SIZE),
              }))
              setViewMode("browse")
            }}
            title="Switch to browse view"
          >
            <LayoutGrid />
            Browse
          </Button>
        )}
        <AddChannel />
        <BulkImport />
        {viewMode === "table" && <ColumnVisibilityButton table={table} />}
      </ChannelsHeader>

      {query.data.total_count === 0 ? (
        <EmptyState
          icon={Tv}
          title="You don't have any channels yet"
          description="Create a channel to get started"
        />
      ) : viewMode === "table" ? (
        <div className="px-[4%]">
          <DataTable
            columns={columns}
            data={tableData}
            storageKey="channels-own"
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
                    rowCount,
                    totalRowCount: query.data.total_count,
                  }
                : undefined
            }
          />
        </div>
      ) : (
        <>
          <ChannelsBrowse channels={pageChannels} />
          <BrowsePagination
            pagination={pagination}
            onPaginationChange={setPagination}
            rowCount={rowCount}
          />
        </>
      )}
    </div>
  )
}

function Channels() {
  const search = Route.useSearch()
  const navigate = useNavigate()
  const loggedIn = isLoggedIn()
  const { user } = useAuth()
  const isAdmin = user?.is_superuser ?? false
  const scope: Scope = loggedIn ? (search.view ?? "mine") : "public"

  const setScope = (next: Scope) => {
    navigate({
      to: "/channels",
      search: next === "mine" ? {} : { view: next },
      replace: true,
    })
  }

  const scopeTabs = loggedIn ? (
    <Tabs value={scope} onValueChange={(value) => setScope(value as Scope)}>
      <TabsList>
        <TabsTrigger value="mine">Owned</TabsTrigger>
        <TabsTrigger value="public">Public</TabsTrigger>
        {isAdmin && <TabsTrigger value="all">All</TabsTrigger>}
      </TabsList>
    </Tabs>
  ) : null

  return (
    <div className="flex flex-col gap-6">
      {scope === "all" && isAdmin ? (
        <AllChannelsView scopeTabs={scopeTabs} />
      ) : scope === "mine" ? (
        <MyChannels scopeTabs={scopeTabs} />
      ) : (
        <PublicChannelsView scopeTabs={scopeTabs} />
      )}
    </div>
  )
}
