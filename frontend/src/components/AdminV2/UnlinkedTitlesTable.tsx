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

import { TitlesService } from "@/client"
import { ColumnVisibilityButton } from "@/components/Common/ColumnVisibilityButton"
import { DataTable, serializeTableQuery } from "@/components/Common/DataTable"
import { DataTableSkeleton } from "@/components/Common/DataTableSkeleton"
import { PageHeader } from "@/components/Common/PageHeader"
import { Button } from "@/components/ui/button"
import { usePersistedJsonState } from "@/hooks/usePersistedState"
import { unlinkedTitleColumns } from "./unlinkedTitleColumns"

// TODO: Validate
export function UnlinkedTitlesTable() {
  const [columnVisibility, setColumnVisibility] =
    usePersistedJsonState<VisibilityState>(
      "admin-v2-unlinked-titles-visibility",
      {
        title_year: false,
        plugin_name: false,
        source_key: false,
        media_type: false,
        link_status: false,
        created_at: false,
      },
    )
  const [pagination, setPagination] = useState<PaginationState>({
    pageIndex: 0,
    pageSize: 100,
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
    queryKey: ["titles", "unlinked", params],
    queryFn: () =>
      TitlesService.adminGetUnlinkedTitles({
        offset: params.offset,
        limit: params.limit,
        inUserChannelsOnly: params.inUserChannelsOnly,
        ...serializeTableQuery(params, unlinkedTitleColumns),
      }),
    placeholderData: keepPreviousData,
    refetchOnWindowFocus: false,
  })

  const rows = query.data?.data

  const table = useReactTable({
    data: rows ?? [],
    columns: unlinkedTitleColumns,
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
      <PageHeader title="Unlinked Titles">
        <Button
          variant={inUserChannelsOnly ? "default" : "outline"}
          onClick={() => {
            setInUserChannelsOnly(!inUserChannelsOnly)
            setPagination({ ...pagination, pageIndex: 0 })
          }}
          title="Switch between every unlinked title and the ones a user's channel holds"
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
            columns={unlinkedTitleColumns}
            data={rows}
            storageKey="admin-v2-unlinked-titles"
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
