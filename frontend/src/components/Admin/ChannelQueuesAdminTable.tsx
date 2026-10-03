// TODO: Validate
import { keepPreviousData, useQuery } from "@tanstack/react-query"
import type {
  ColumnFiltersState,
  PaginationState,
  SortingState,
  VisibilityState,
} from "@tanstack/react-table"
import { getCoreRowModel, useReactTable } from "@tanstack/react-table"
import { useState } from "react"

import { ChannelsService } from "@/client"
import { ColumnVisibilityButton } from "@/components/Common/ColumnVisibilityButton"
import { DataTable, serializeTableQuery } from "@/components/Common/DataTable"
import { DataTableSkeleton } from "@/components/Common/DataTableSkeleton"
import { PageHeader } from "@/components/Common/PageHeader"
import { usePersistedJsonState } from "@/hooks/usePersistedState"
import { channelQueueColumns } from "./channelQueueColumns"

// TODO: Validate
export function ChannelQueuesAdminTable() {
  const [pagination, setPagination] = useState<PaginationState>({
    pageIndex: 0,
    pageSize: 10,
  })
  const [sortOptions, setSortOptions] = useState<SortingState>([])
  const [filterOptions, setFilterOptions] = useState<ColumnFiltersState>([])
  const [columnVisibility, setColumnVisibility] =
    usePersistedJsonState<VisibilityState>(
      "admin-channel-queues-column-visibility",
      {},
    )

  const params = {
    offset: pagination.pageIndex * pagination.pageSize,
    limit: pagination.pageSize,
    sortOptions,
    filterOptions,
  }

  const query = useQuery({
    queryKey: [
      "admin-channel-queues",
      params.offset,
      params.limit,
      sortOptions,
      filterOptions,
    ],
    queryFn: () =>
      ChannelsService.getAllChannelQueues({
        offset: params.offset,
        limit: params.limit,
        ...serializeTableQuery(params, channelQueueColumns),
      }),
    placeholderData: keepPreviousData,
    refetchOnWindowFocus: false,
  })

  const isServer = query.data?.is_server_side ?? false
  const entries = query.data?.data

  const table = useReactTable({
    data: entries ?? [],
    columns: channelQueueColumns,
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
      <PageHeader title="All Channel Queues">
        <ColumnVisibilityButton table={table} />
      </PageHeader>
      <div className="px-[4%]">
        {!entries ? (
          <DataTableSkeleton table={table} />
        ) : (
          <DataTable
            columns={channelQueueColumns}
            data={entries}
            storageKey="admin-channel-queues"
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
