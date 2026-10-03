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

import { TitlesService } from "@/client"
import { ColumnVisibilityButton } from "@/components/Common/ColumnVisibilityButton"
import { DataTable, serializeTableQuery } from "@/components/Common/DataTable"
import { DataTableSkeleton } from "@/components/Common/DataTableSkeleton"
import { PageHeader } from "@/components/Common/PageHeader"
import { usePersistedJsonState } from "@/hooks/usePersistedState"
import { titleLinkHistoryColumns } from "./titleLinkHistoryColumns"
import { TITLE_LINK_HISTORY_QUERY_KEY } from "./titleLinkHistoryQuery"

const STORAGE_KEY = "admin-v2-title-link-history"

const PAGE_SIZE = 100

// TODO: Validate
export function TitleLinkHistoryTable() {
  const [columnVisibility, setColumnVisibility] =
    usePersistedJsonState<VisibilityState>(`${STORAGE_KEY}-visibility`, {
      source_key: false,
      plugin_name: false,
      title_year: false,
      media_type: false,
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
    queryKey: [...TITLE_LINK_HISTORY_QUERY_KEY, params],
    queryFn: () =>
      TitlesService.adminGetTitleLinkHistory({
        offset: params.offset,
        limit: params.limit,
        ...serializeTableQuery(params, titleLinkHistoryColumns),
      }),
    placeholderData: keepPreviousData,
    refetchOnWindowFocus: false,
  })

  const rows = query.data?.data

  const table = useReactTable({
    data: rows ?? [],
    columns: titleLinkHistoryColumns,
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
      <PageHeader title="Title Link History">
        <ColumnVisibilityButton table={table} />
      </PageHeader>
      <div className="px-[4%]">
        {!rows ? (
          <DataTableSkeleton table={table} />
        ) : (
          <DataTable
            columns={titleLinkHistoryColumns}
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
