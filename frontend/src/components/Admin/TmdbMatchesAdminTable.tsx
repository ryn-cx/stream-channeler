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

import { EpisodesService } from "@/client"
import { ColumnVisibilityButton } from "@/components/Common/ColumnVisibilityButton"
import { DataTable, serializeTableQuery } from "@/components/Common/DataTable"
import { DataTableSkeleton } from "@/components/Common/DataTableSkeleton"
import { PageHeader } from "@/components/Common/PageHeader"
import { usePersistedJsonState } from "@/hooks/usePersistedState"
import {
  TMDB_MATCH_DEFAULT_VISIBILITY,
  tmdbMatchColumns,
} from "./tmdbMatchColumns"
import { TMDB_MATCHES_QUERY_KEY } from "./tmdbMatchesQuery"

const STORAGE_KEY = "admin-tmdb-matches"

// Working through these is done a page at a time, and the closest TMDB episode
// for each is worked out by comparing names, so a page is kept small.
const PAGE_SIZE = 20

// TODO: Validate
export function TmdbMatchesAdminTable() {
  const [columnVisibility, setColumnVisibility] =
    usePersistedJsonState<VisibilityState>(
      `${STORAGE_KEY}-visibility`,
      TMDB_MATCH_DEFAULT_VISIBILITY,
    )
  const [pagination, setPagination] = useState<PaginationState>({
    pageIndex: 0,
    pageSize: PAGE_SIZE,
  })
  const [sortOptions, setSortOptions] = useState<SortingState>([])
  const [filterOptions, setFilterOptions] = useState<ColumnFiltersState>([])

  const params = {
    offset: pagination.pageIndex * pagination.pageSize,
    limit: pagination.pageSize,
    sortOptions,
    filterOptions,
  }

  const query = useQuery({
    queryKey: [...TMDB_MATCHES_QUERY_KEY, params],
    queryFn: () =>
      EpisodesService.adminGetUnmatchedEpisodes({
        offset: params.offset,
        limit: params.limit,
        ...serializeTableQuery(params, tmdbMatchColumns),
      }),
    // The page already on screen is kept while the next one is read, so paging
    // and sorting do not blank the table on the way.
    placeholderData: keepPreviousData,
    refetchOnWindowFocus: false,
  })

  const episodes = query.data?.data

  const table = useReactTable({
    data: episodes ?? [],
    columns: tmdbMatchColumns,
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
      <PageHeader title="TMDB Matches">
        <ColumnVisibilityButton table={table} />
      </PageHeader>
      <div className="px-[4%]">
        {!episodes ? (
          <DataTableSkeleton table={table} />
        ) : (
          <DataTable
            columns={tmdbMatchColumns}
            data={episodes}
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
