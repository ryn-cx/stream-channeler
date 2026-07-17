// TODO: Validate
import type {
  ColumnFiltersState,
  PaginationState,
  SortingState,
  VisibilityState,
} from "@tanstack/react-table"
import { getCoreRowModel, useReactTable } from "@tanstack/react-table"
import { Globe } from "lucide-react"
import type { ReactNode } from "react"
import { useState } from "react"

import AddChannel from "@/components/Channels/ChannelList/AddChannel"
import { BulkImport } from "@/components/Channels/ChannelList/BulkImport"
import { ChannelsBrowse } from "@/components/Channels/ChannelList/ChannelsBrowse"
import { ChannelsHeader } from "@/components/Channels/ChannelList/ChannelsHeader"
import { publicChannelColumns } from "@/components/Channels/ChannelList/publicColumns"
import { useScopedChannels } from "@/components/Channels/ChannelList/useScopedChannels"
import {
  BrowsePagination,
  DEFAULT_BROWSE_PAGE_SIZE,
  MAX_BROWSE_PAGE_SIZE,
} from "@/components/Common/BrowsePagination"
import { ColumnVisibilityButton } from "@/components/Common/ColumnVisibilityButton"
import { DataTable } from "@/components/Common/DataTable"
import { EmptyState } from "@/components/Common/EmptyState"
import { type ViewMode, ViewModeTabs } from "@/components/Common/ViewModeTabs"
import PendingChannelList from "@/components/Pending/PendingChannelList"
import useAuth from "@/hooks/useAuth"
import {
  usePersistedJsonState,
  usePersistedState,
} from "@/hooks/usePersistedState"

export function PublicChannelsView({ scopeTabs }: { scopeTabs: ReactNode }) {
  const { user } = useAuth()
  const isAdmin = user?.is_superuser ?? false
  // Zero-based page index, matching the offset/limit query params.
  const [pagination, setPagination] = useState<PaginationState>({
    pageIndex: 0,
    pageSize: DEFAULT_BROWSE_PAGE_SIZE,
  })
  const [sortOptions, setSortOptions] = useState<SortingState>([])
  const [filterOptions, setFilterOptions] = useState<ColumnFiltersState>([])
  const [viewMode, setViewMode] = usePersistedState<ViewMode>(
    "public-channels-list-view",
    "browse",
  )
  const [columnVisibility, setColumnVisibility] =
    usePersistedJsonState<VisibilityState>(
      "public-channels-column-visibility",
      {},
    )

  // The table view lets the page size grow past what browse offers, so clamp it
  // back down to browse's maximum on the way in.
  const changeViewMode = (mode: ViewMode) => {
    if (mode === "browse") {
      setPagination((current) => ({
        pageIndex: 0,
        pageSize: Math.min(current.pageSize, MAX_BROWSE_PAGE_SIZE),
      }))
    }
    setViewMode(mode)
  }

  const columns = publicChannelColumns(isAdmin)
  const query = useScopedChannels(
    "public",
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
  const allRows = query.data?.data ?? []
  const pageStart = pagination.pageIndex * pagination.pageSize
  const browseRows = isServer
    ? allRows
    : allRows.slice(pageStart, pageStart + pagination.pageSize)
  const rowCount = isServer ? (query.data?.filtered_count ?? 0) : allRows.length

  const table = useReactTable({
    data: allRows,
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
          icon={Globe}
          title="No public channels yet"
          description="Channels shared publicly by any user will show up here."
        />
      ) : viewMode === "table" ? (
        <div className="px-[4%]">
          <DataTable
            columns={columns}
            data={allRows}
            storageKey="public-channels"
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
          <ChannelsBrowse
            channels={browseRows}
            readOnly
            showChannelNumber={false}
          />

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
