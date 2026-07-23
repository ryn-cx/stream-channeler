// TODO: Validate
import { useQuery } from "@tanstack/react-query"
import { createFileRoute, useNavigate } from "@tanstack/react-router"
import type {
  ColumnFiltersState,
  SortingState,
  VisibilityState,
} from "@tanstack/react-table"
import { getCoreRowModel, useReactTable } from "@tanstack/react-table"
import { Tv } from "lucide-react"
import { type ReactNode, useMemo, useState } from "react"
import { ChannelsService } from "@/client"
import AddChannel from "@/components/Channels/ChannelList/AddChannel"
import { AllChannelsView } from "@/components/Channels/ChannelList/AllChannelsView"
import { BulkImport } from "@/components/Channels/ChannelList/BulkImport"
import {
  ChannelsBrowse,
  sortOwnedChannels,
} from "@/components/Channels/ChannelList/ChannelsBrowse"
import { ChannelsHeader } from "@/components/Channels/ChannelList/ChannelsHeader"
import { ownedChannelColumns } from "@/components/Channels/ChannelList/columns"
import { FavoriteChannelsView } from "@/components/Channels/ChannelList/FavoriteChannelsView"
import { PublicChannelsView } from "@/components/Channels/ChannelList/PublicChannelsView"
import { useScopedChannels } from "@/components/Channels/ChannelList/useScopedChannels"
import {
  BrowsePagination,
  MAX_BROWSE_PAGE_SIZE,
  useBrowsePagination,
} from "@/components/Common/BrowsePagination"
import { ColumnVisibilityButton } from "@/components/Common/ColumnVisibilityButton"
import { DataTable } from "@/components/Common/DataTable"
import { EmptyState } from "@/components/Common/EmptyState"
import { type ViewMode, ViewModeTabs } from "@/components/Common/ViewModeTabs"
import PendingChannelList from "@/components/Pending/PendingChannelList"
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"
import useAuth, { isLoggedIn } from "@/hooks/useAuth"
import { usePersistedJsonState } from "@/hooks/usePersistedState"

type Scope = "owned" | "favorites" | "public" | "all"

type ChannelsSearch = {
  view?: "owned" | "favorites" | "public" | "all"
  mode?: ViewMode
}

export const Route = createFileRoute("/_layout/channels/")({
  component: Channels,
  validateSearch: (search: Record<string, unknown>): ChannelsSearch => ({
    view:
      search.view === "owned" ||
      search.view === "favorites" ||
      search.view === "public" ||
      search.view === "all"
        ? search.view
        : undefined,
    mode: search.mode === "table" ? "table" : undefined,
  }),
  head: () => ({
    meta: [
      {
        title: "Channels - Stream Channeler",
      },
    ],
  }),
})

function MyChannels({
  scopeTabs,
  viewMode,
  onViewModeChange,
}: {
  scopeTabs: ReactNode
  viewMode: ViewMode
  onViewModeChange: (mode: ViewMode) => void
}) {
  const { user } = useAuth()
  const isAdmin = user?.is_superuser ?? false
  const [columnVisibility, setColumnVisibility] =
    usePersistedJsonState<VisibilityState>("channels-column-visibility", {
      id: false,
    })
  const [pagination, setPagination] = useBrowsePagination(
    "channels-own-browse-page-size",
  )
  const [sortOptions, setSortOptions] = useState<SortingState>([])
  const [filterOptions, setFilterOptions] = useState<ColumnFiltersState>([])

  // The table view lets the page size grow past what browse offers, so clamp it
  // back down to browse's maximum on the way in.
  const changeViewMode = (mode: ViewMode) => {
    if (mode === "browse") {
      setPagination((current) => ({
        pageIndex: 0,
        pageSize: Math.min(current.pageSize, MAX_BROWSE_PAGE_SIZE),
      }))
    }
    onViewModeChange(mode)
  }

  const columns = ownedChannelColumns(isAdmin)
  const query = useScopedChannels(
    "owned",
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
      <ChannelsHeader
        scopeTabs={scopeTabs}
        viewTabs={
          <ViewModeTabs value={viewMode} onValueChange={changeViewMode} />
        }
      >
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

// When no scope is pinned in the URL, land on the most relevant populated tab:
// favorites if the user has any, otherwise owned, otherwise public.
function useDefaultScope(enabled: boolean): {
  scope: Scope
  isPending: boolean
} {
  const favoritesQuery = useQuery({
    queryKey: ["channels", "favorites", "default-count"],
    queryFn: () =>
      ChannelsService.getChannels({ scope: "favorites", offset: 0, limit: 1 }),
    enabled,
    refetchOnWindowFocus: false,
  })
  const ownedQuery = useQuery({
    queryKey: ["channels", "owned", "default-count"],
    queryFn: () =>
      ChannelsService.getChannels({ scope: "owned", offset: 0, limit: 1 }),
    enabled,
    refetchOnWindowFocus: false,
  })

  if ((favoritesQuery.data?.total_count ?? 0) > 0) {
    return { scope: "favorites", isPending: false }
  }
  if ((ownedQuery.data?.total_count ?? 0) > 0) {
    return { scope: "owned", isPending: false }
  }

  const isPending =
    enabled && (favoritesQuery.isPending || ownedQuery.isPending)
  return { scope: "public", isPending }
}

function Channels() {
  const search = Route.useSearch()
  const navigate = useNavigate()
  const loggedIn = isLoggedIn()
  const { user } = useAuth()
  const isAdmin = user?.is_superuser ?? false

  const needsDefaultScope = loggedIn && search.view === undefined
  const { scope: defaultScope, isPending: defaultScopePending } =
    useDefaultScope(needsDefaultScope)
  const scope: Scope = loggedIn ? (search.view ?? defaultScope) : "public"
  const viewMode: ViewMode = search.mode ?? "browse"

  // Both tabs live in the URL, so each write preserves the other's value. The
  // scope must be written explicitly — its default is resolved from channel counts,
  // so an absent view would send the user back to that resolved tab rather than the
  // one they clicked. The browse view stays a droppable default to keep the URL clean.
  const buildSearch = (
    nextScope: Scope,
    nextMode: ViewMode,
  ): ChannelsSearch => ({
    view: nextScope,
    mode: nextMode === "browse" ? undefined : nextMode,
  })

  const setScope = (next: Scope) => {
    navigate({
      to: "/channels",
      search: buildSearch(next, viewMode),
      replace: true,
    })
  }

  const setViewMode = (mode: ViewMode) => {
    navigate({
      to: "/channels",
      search: buildSearch(scope, mode),
      replace: true,
    })
  }

  const scopeTabs = loggedIn ? (
    <Tabs value={scope} onValueChange={(value) => setScope(value as Scope)}>
      <TabsList>
        <TabsTrigger value="owned">Owned</TabsTrigger>
        <TabsTrigger value="favorites">Favorites</TabsTrigger>
        <TabsTrigger value="public">Public</TabsTrigger>
        {isAdmin && <TabsTrigger value="all">All</TabsTrigger>}
      </TabsList>
    </Tabs>
  ) : null

  // Hold on a neutral pending state until the counts decide the tab, so the page
  // doesn't flash the fallback scope before settling on the resolved one.
  if (defaultScopePending) {
    return (
      <div className="flex flex-col gap-6">
        <ChannelsHeader scopeTabs={scopeTabs} />
        <PendingChannelList />
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-6">
      {scope === "all" && isAdmin ? (
        <AllChannelsView
          scopeTabs={scopeTabs}
          viewMode={viewMode}
          onViewModeChange={setViewMode}
        />
      ) : scope === "owned" ? (
        <MyChannels
          scopeTabs={scopeTabs}
          viewMode={viewMode}
          onViewModeChange={setViewMode}
        />
      ) : scope === "favorites" ? (
        <FavoriteChannelsView
          scopeTabs={scopeTabs}
          viewMode={viewMode}
          onViewModeChange={setViewMode}
        />
      ) : (
        <PublicChannelsView
          scopeTabs={scopeTabs}
          viewMode={viewMode}
          onViewModeChange={setViewMode}
        />
      )}
    </div>
  )
}
