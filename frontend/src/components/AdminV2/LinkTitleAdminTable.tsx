// TODO: Validate
import { keepPreviousData, useQuery } from "@tanstack/react-query"
import type {
  ColumnFiltersState,
  PaginationState,
  SortingState,
  VisibilityState,
} from "@tanstack/react-table"
import { getCoreRowModel, useReactTable } from "@tanstack/react-table"
import { Globe, Users } from "lucide-react"
import { useState } from "react"

import { UnmatchedTitlesService } from "@/client"
import { ColumnVisibilityButton } from "@/components/Common/ColumnVisibilityButton"
import { DataTable, serializeTableQuery } from "@/components/Common/DataTable"
import { DataTableSkeleton } from "@/components/Common/DataTableSkeleton"
import { PageHeader } from "@/components/Common/PageHeader"
import { Button } from "@/components/ui/button"
import { usePersistedJsonState } from "@/hooks/usePersistedState"
import { linkTitleColumns } from "./linkTitleColumns"
import { UNMATCHED_TITLES_QUERY_KEY } from "./unmatchedTitlesQuery"

const STORAGE_KEY = "admin-v2-link-title"

const PAGE_SIZE = 100

// TODO: Validate
export function LinkTitleAdminTable() {
  const [columnVisibility, setColumnVisibility] =
    usePersistedJsonState<VisibilityState>(`${STORAGE_KEY}-visibility`, {})
  const [pagination, setPagination] = useState<PaginationState>({
    pageIndex: 0,
    pageSize: PAGE_SIZE,
  })
  const [sortOptions, setSortOptions] = useState<SortingState>([
    { id: "title_name", desc: false },
  ])
  const [filterOptions, setFilterOptions] = useState<ColumnFiltersState>([])
  const [inUserChannelsOnly, setInUserChannelsOnly] = useState(true)

  const params = {
    offset: pagination.pageIndex * pagination.pageSize,
    limit: pagination.pageSize,
    sortOptions,
    filterOptions,
    inUserChannelsOnly,
  }

  const query = useQuery({
    queryKey: [...UNMATCHED_TITLES_QUERY_KEY, params],
    queryFn: () =>
      UnmatchedTitlesService.adminGetUnmatchedTitles({
        offset: params.offset,
        limit: params.limit,
        inUserChannelsOnly: params.inUserChannelsOnly,
        ...serializeTableQuery(params, linkTitleColumns),
      }),
    // The page already on screen is kept while the next one is read, so paging
    // and sorting do not blank the table on the way.
    placeholderData: keepPreviousData,
    refetchOnWindowFocus: false,
  })

  const rows = query.data?.data

  const table = useReactTable({
    data: rows ?? [],
    columns: linkTitleColumns,
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
      <PageHeader title="Link Title">
        <Button
          variant={inUserChannelsOnly ? "default" : "outline"}
          onClick={() => {
            setInUserChannelsOnly(!inUserChannelsOnly)
            setPagination({ ...pagination, pageIndex: 0 })
          }}
          title="Switch between every title waiting on a source and the ones a user's channel holds"
        >
          {inUserChannelsOnly ? <Users /> : <Globe />}
          {inUserChannelsOnly ? "In user channels" : "All titles"}
        </Button>
        <ColumnVisibilityButton table={table} />
      </PageHeader>
      <div className="px-[4%]">
        {!rows ? (
          <DataTableSkeleton table={table} />
        ) : (
          <DataTable
            columns={linkTitleColumns}
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
