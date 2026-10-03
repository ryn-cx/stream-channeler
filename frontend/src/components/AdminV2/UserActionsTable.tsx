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

import { UserActionsService } from "@/client"
import { ColumnVisibilityButton } from "@/components/Common/ColumnVisibilityButton"
import { DataTable, serializeTableQuery } from "@/components/Common/DataTable"
import { DataTableSkeleton } from "@/components/Common/DataTableSkeleton"
import { PageHeader } from "@/components/Common/PageHeader"
import { usePersistedJsonState } from "@/hooks/usePersistedState"
import { userActionColumns } from "./userActionColumns"
import { USER_ACTIONS_QUERY_KEY } from "./userActionsQuery"

const STORAGE_KEY = "admin-v2-user-actions"

const PAGE_SIZE = 100

// TODO: Validate
export function UserActionsTable() {
  const [columnVisibility, setColumnVisibility] =
    usePersistedJsonState<VisibilityState>(`${STORAGE_KEY}-visibility`, {
      email: false,
    })
  const [pagination, setPagination] = useState<PaginationState>({
    pageIndex: 0,
    pageSize: PAGE_SIZE,
  })
  const [sortOptions, setSortOptions] = useState<SortingState>([
    { id: "created_at", desc: true },
  ])
  const [filterOptions, setFilterOptions] = useState<ColumnFiltersState>([])

  const params = {
    offset: pagination.pageIndex * pagination.pageSize,
    limit: pagination.pageSize,
    sortOptions,
    filterOptions,
  }

  const query = useQuery({
    queryKey: [...USER_ACTIONS_QUERY_KEY, params],
    queryFn: () =>
      UserActionsService.adminGetUserActions({
        offset: params.offset,
        limit: params.limit,
        ...serializeTableQuery(params, userActionColumns),
      }),
    placeholderData: keepPreviousData,
    refetchOnWindowFocus: false,
  })

  const rows = query.data?.data

  const table = useReactTable({
    data: rows ?? [],
    columns: userActionColumns,
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
      <PageHeader title="User Actions">
        <ColumnVisibilityButton table={table} />
      </PageHeader>
      <div className="px-[4%]">
        {!rows ? (
          <DataTableSkeleton table={table} />
        ) : (
          <DataTable
            columns={userActionColumns}
            data={rows}
            storageKey={STORAGE_KEY}
            columnVisibility={columnVisibility}
            onColumnVisibilityChange={setColumnVisibility}
            serverSide={{
              pagination,
              sortOptions,
              filterOptions,
              onPaginationChange: setPagination,
              onSortOptionsChange: setSortOptions,
              onFilterOptionsChange: setFilterOptions,
              rowCount: query.data?.filtered_count ?? 0,
              totalRowCount: query.data?.total_count ?? 0,
            }}
          />
        )}
      </div>
    </div>
  )
}
