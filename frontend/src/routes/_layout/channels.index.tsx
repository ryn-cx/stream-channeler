// TODO: Validate
import { createFileRoute, useNavigate } from "@tanstack/react-router"
import type {
  ColumnDef,
  ColumnFiltersState,
  SortingState,
} from "@tanstack/react-table"
import { getCoreRowModel, useReactTable } from "@tanstack/react-table"
import { Globe, type LucideIcon, Star, Tv } from "lucide-react"
import { type ComponentProps, type ReactNode, useState } from "react"
import { channelColumns } from "@/components/Admin/channelColumns"
import AddChannel from "@/components/Channels/ChannelList/AddChannel"
import { BulkImport } from "@/components/Channels/ChannelList/BulkImport"
import { ChannelsBrowseSection } from "@/components/Channels/ChannelList/ChannelsBrowseSection"
import { ChannelsHeader } from "@/components/Channels/ChannelList/ChannelsHeader"
import { ownedChannelColumns } from "@/components/Channels/ChannelList/columns"
import { publicChannelColumns } from "@/components/Channels/ChannelList/publicColumns"
import { useChannelColumnVisibility } from "@/components/Channels/ChannelList/useChannelColumnVisibility"
import {
  type ChannelRow,
  useScopedChannels,
} from "@/components/Channels/ChannelList/useScopedChannels"
import {
  MAX_BROWSE_PAGE_SIZE,
  useBrowsePagination,
} from "@/components/Common/BrowsePagination"
import { ColumnVisibilityButton } from "@/components/Common/ColumnVisibilityButton"
import { DataTable } from "@/components/Common/DataTable"
import { EmptyState } from "@/components/Common/EmptyState"
import {
  type ViewMode,
  ViewModeToggle,
} from "@/components/Common/ViewModeToggle"
import PendingChannelList from "@/components/Pending/PendingChannelList"
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"
import useAuth, { isLoggedIn } from "@/hooks/useAuth"
import { usePersistedState } from "@/hooks/usePersistedState"

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

// Everything that differs between the four scopes. The rest of the view — query,
// pagination, table/browse switch, header — is identical for all of them.
interface ScopeView {
  columns: (isAdmin: boolean) => ColumnDef<ChannelRow>[]
  // "all" is an admin-only scope, so it always queries with admin privileges.
  queryAsAdmin: (isAdmin: boolean) => boolean
  tableStorageKey: string
  pageSizeStorageKey: string
  emptyIcon: LucideIcon
  emptyTitle: string
  emptyDescription: string
  browse: Partial<
    Pick<
      ComponentProps<typeof ChannelsBrowseSection>,
      "sortByNumber" | "readOnly" | "personalizable" | "showChannelNumber"
    >
  >
}

const SCOPE_VIEWS: Record<Scope, ScopeView> = {
  owned: {
    columns: (isAdmin) => ownedChannelColumns(isAdmin),
    queryAsAdmin: (isAdmin) => isAdmin,
    tableStorageKey: "channels-own",
    pageSizeStorageKey: "channels-own-browse-page-size",
    emptyIcon: Tv,
    emptyTitle: "You don't have any channels yet",
    emptyDescription: "Create a channel to get started",
    browse: { sortByNumber: true },
  },
  favorites: {
    columns: (isAdmin) => publicChannelColumns(isAdmin),
    queryAsAdmin: (isAdmin) => isAdmin,
    tableStorageKey: "favorite-channels",
    pageSizeStorageKey: "channels-favorites-browse-page-size",
    emptyIcon: Star,
    emptyTitle: "No favorite channels yet",
    emptyDescription: "Star a channel to keep it here.",
    browse: { sortByNumber: true, readOnly: true, personalizable: true },
  },
  public: {
    columns: () => publicChannelColumns(false),
    queryAsAdmin: (isAdmin) => isAdmin,
    tableStorageKey: "public-channels",
    pageSizeStorageKey: "channels-public-browse-page-size",
    emptyIcon: Globe,
    emptyTitle: "No public channels yet",
    emptyDescription: "Channels shared publicly by any user will show up here.",
    browse: { readOnly: true, showChannelNumber: false },
  },
  all: {
    columns: () => channelColumns as ColumnDef<ChannelRow>[],
    queryAsAdmin: () => true,
    tableStorageKey: "all-channels",
    pageSizeStorageKey: "channels-all-browse-page-size",
    emptyIcon: Tv,
    emptyTitle: "No channels yet",
    emptyDescription: "Channels created by any user will show up here.",
    browse: { readOnly: true },
  },
}

// TODO: Validate
function ChannelsView({
  scope,
  scopeTabs,
  viewMode,
  onViewModeChange,
}: {
  scope: Scope
  scopeTabs: ReactNode
  viewMode: ViewMode
  onViewModeChange: (mode: ViewMode) => void
}) {
  const { user } = useAuth()
  const isAdmin = user?.is_superuser ?? false
  const view = SCOPE_VIEWS[scope]
  const [columnVisibility, setColumnVisibility] = useChannelColumnVisibility()
  const [pagination, setPagination] = useBrowsePagination(
    view.pageSizeStorageKey,
  )
  const [sortOptions, setSortOptions] = useState<SortingState>([])
  const [filterOptions, setFilterOptions] = useState<ColumnFiltersState>([])

  // The table view lets the page size grow past what browse offers, so clamp it
  // back down to browse's maximum on the way in.
  // TODO: Validate
  const changeViewMode = (mode: ViewMode) => {
    if (mode === "browse") {
      setPagination((current) => ({
        pageIndex: 0,
        pageSize: Math.min(current.pageSize, MAX_BROWSE_PAGE_SIZE),
      }))
    }
    onViewModeChange(mode)
  }

  const columns = view.columns(isAdmin)
  const query = useScopedChannels(
    scope,
    view.queryAsAdmin(isAdmin),
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
  const rowCount = isServer
    ? (query.data?.filtered_count ?? 0)
    : tableData.length

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
          <ViewModeToggle value={viewMode} onValueChange={changeViewMode} />
        }
      >
        <AddChannel />
        <BulkImport />
        {viewMode === "table" && <ColumnVisibilityButton table={table} />}
      </ChannelsHeader>

      {query.data.total_count === 0 ? (
        <EmptyState
          icon={view.emptyIcon}
          title={view.emptyTitle}
          description={view.emptyDescription}
        />
      ) : viewMode === "table" ? (
        <div className="px-[4%]">
          <DataTable
            columns={columns}
            data={tableData}
            storageKey={view.tableStorageKey}
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
        <ChannelsBrowseSection
          rows={tableData}
          isServer={isServer}
          serverRowCount={rowCount}
          pagination={pagination}
          onPaginationChange={setPagination}
          {...view.browse}
        />
      )}
    </div>
  )
}

const LAST_SCOPE_KEY = "channels-last-scope"

// TODO: Validate
function isScope(value: string): value is Scope {
  return (
    value === "owned" ||
    value === "favorites" ||
    value === "public" ||
    value === "all"
  )
}

// TODO: Validate
function Channels() {
  const search = Route.useSearch()
  const navigate = useNavigate()
  const loggedIn = isLoggedIn()
  const { user } = useAuth()
  const isAdmin = user?.is_superuser ?? false

  // With no scope pinned in the URL, return to the tab the user last picked.
  const [lastScope, setLastScope] = usePersistedState<Scope>(
    LAST_SCOPE_KEY,
    "public",
  )
  const rememberedScope: Scope =
    isScope(lastScope) && (lastScope !== "all" || isAdmin)
      ? lastScope
      : "public"
  const scope: Scope = loggedIn ? (search.view ?? rememberedScope) : "public"
  const viewMode: ViewMode = search.mode ?? "browse"

  // Both tabs live in the URL, so each write preserves the other's value. The
  // scope must be written explicitly — its default is resolved from channel counts,
  // so an absent view would send the user back to that resolved tab rather than the
  // one they clicked. The browse view stays a droppable default to keep the URL clean.
  // TODO: Validate
  const buildSearch = (
    nextScope: Scope,
    nextMode: ViewMode,
  ): ChannelsSearch => ({
    view: nextScope,
    mode: nextMode === "browse" ? undefined : nextMode,
  })

  // TODO: Validate
  const setScope = (next: Scope) => {
    setLastScope(next)
    navigate({
      to: "/channels",
      search: buildSearch(next, viewMode),
      replace: true,
    })
  }

  // TODO: Validate
  const setViewMode = (mode: ViewMode) => {
    navigate({
      to: "/channels",
      search: buildSearch(scope, mode),
      replace: true,
    })
  }

  // TODO: Validate
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

  // The "all" scope is admin-only, so a non-admin holding it in the URL falls
  // back to public. Keying on the scope remounts the view, dropping the previous
  // scope's sort and filter state rather than applying it to different columns.
  const resolvedScope: Scope = scope === "all" && !isAdmin ? "public" : scope

  return (
    <div className="flex flex-col gap-6">
      <ChannelsView
        key={resolvedScope}
        scope={resolvedScope}
        scopeTabs={scopeTabs}
        viewMode={viewMode}
        onViewModeChange={setViewMode}
      />
    </div>
  )
}
