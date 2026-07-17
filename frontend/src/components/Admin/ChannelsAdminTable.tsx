// TODO: Validate
import type {
  ColumnFiltersState,
  PaginationState,
  SortingState,
  VisibilityState,
} from "@tanstack/react-table"
import { getCoreRowModel, useReactTable } from "@tanstack/react-table"
import { useState } from "react"

import { useScopedChannels } from "@/components/Channels/ChannelList/useScopedChannels"
import { ColumnVisibilityButton } from "@/components/Common/ColumnVisibilityButton"
import { DataTable } from "@/components/Common/DataTable"
import { DataTableSkeleton } from "@/components/Common/DataTableSkeleton"
import { PageHeader } from "@/components/Common/PageHeader"
import { usePersistedJsonState } from "@/hooks/usePersistedState"
import { channelColumns } from "./channelColumns"

export function ChannelsAdminTable() {
  const [pagination, setPagination] = useState<PaginationState>({
    pageIndex: 0,
    pageSize: 10,
  })
  const [sortOptions, setSortOptions] = useState<SortingState>([])
  const [filterOptions, setFilterOptions] = useState<ColumnFiltersState>([])
  const [columnVisibility, setColumnVisibility] =
    usePersistedJsonState<VisibilityState>(
      "admin-channels-column-visibility",
      {},
    )

  const query = useScopedChannels(
    "all",
    true,
    {
      offset: pagination.pageIndex * pagination.pageSize,
      limit: pagination.pageSize,
      sortOptions,
      filterOptions,
    },
    channelColumns,
  )

  const isServer = query.data?.is_server_side ?? false
  const channels = query.data?.data

  const table = useReactTable({
    data: channels ?? [],
    columns: channelColumns,
    state: { columnVisibility },
    onColumnVisibilityChange: setColumnVisibility,
    getCoreRowModel: getCoreRowModel(),
  })

  return (
    <div
      className={
        query.isPlaceholderData
          ? "opacity-60 transition-opacity duration-200"
          : undefined
      }
    >
      <PageHeader title="All Channels">
        <ColumnVisibilityButton table={table} />
      </PageHeader>
      <div className="px-[4%]">
        {!channels ? (
          <DataTableSkeleton table={table} />
        ) : (
          <DataTable
            columns={channelColumns}
            data={channels}
            storageKey="admin-channels"
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
        )}
      </div>
    </div>
  )
}
