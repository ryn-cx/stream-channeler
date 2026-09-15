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
import { useMemo, useState } from "react"

import { EpisodesService } from "@/client"
import { TmdbLinkMultipleButton } from "@/components/Admin/TmdbLinkMultipleButton"
import {
  asTmdbMatchRows,
  TMDB_MATCH_DEFAULT_VISIBILITY,
  type TmdbMatchRow,
  tmdbMatchColumns,
} from "@/components/Admin/tmdbMatchColumns"
import { OpenEpisodeEditorProvider } from "@/components/Admin/tmdbMatchEditing"
import {
  TMDB_MATCHES_QUERY_KEY,
  useSettlingTmdbMatchIds,
} from "@/components/Admin/tmdbMatchesQuery"
import { TmdbMatchSelectionProvider } from "@/components/Admin/tmdbMatchSelection"
import { ColumnVisibilityButton } from "@/components/Common/ColumnVisibilityButton"
import { DataTable, serializeTableQuery } from "@/components/Common/DataTable"
import { DataTableSkeleton } from "@/components/Common/DataTableSkeleton"
import { PageHeader } from "@/components/Common/PageHeader"
import EditEpisode from "@/components/Episodes/Edit"
import { Button } from "@/components/ui/button"
import { usePersistedJsonState } from "@/hooks/usePersistedState"

const STORAGE_KEY = "admin-v2-link-episode"

const PAGE_SIZE = 100

// TODO: Validate
export function LinkEpisodeAdminTable() {
  const [columnVisibility, setColumnVisibility] =
    usePersistedJsonState<VisibilityState>(
      `${STORAGE_KEY}-visibility`,
      TMDB_MATCH_DEFAULT_VISIBILITY,
    )
  const [pagination, setPagination] = useState<PaginationState>({
    pageIndex: 0,
    pageSize: PAGE_SIZE,
  })
  const [sortOptions, setSortOptions] = useState<SortingState>([
    { id: "summary", desc: false },
  ])
  const [filterOptions, setFilterOptions] = useState<ColumnFiltersState>([])
  const [inUserChannelsOnly, setInUserChannelsOnly] = useState(true)
  const [editing, setEditing] = useState<TmdbMatchRow | null>(null)

  const params = {
    offset: pagination.pageIndex * pagination.pageSize,
    limit: pagination.pageSize,
    sortOptions,
    filterOptions,
    inUserChannelsOnly,
  }

  const query = useQuery({
    queryKey: [...TMDB_MATCHES_QUERY_KEY, "v2", params],
    queryFn: () =>
      EpisodesService.adminGetUnmatchedEpisodes({
        offset: params.offset,
        limit: params.limit,
        inUserChannelsOnly: params.inUserChannelsOnly,
        ...serializeTableQuery(params, tmdbMatchColumns),
      }),
    // The page already on screen is kept while the next one is read, so paging
    // and sorting do not blank the table on the way.
    placeholderData: keepPreviousData,
    refetchOnWindowFocus: false,
  })

  const settlingIds = useSettlingTmdbMatchIds(query.dataUpdatedAt)
  const rows = useMemo(
    () => (query.data ? asTmdbMatchRows(query.data.data) : undefined),
    [query.data],
  )
  const episodes = useMemo(
    () => rows?.filter((row) => !settlingIds.has(row.episode.id)),
    [rows, settlingIds],
  )
  const settledHere = (query.data?.data.length ?? 0) - (episodes?.length ?? 0)

  const table = useReactTable({
    data: episodes ?? [],
    columns: tmdbMatchColumns,
    state: { columnVisibility },
    onColumnVisibilityChange: setColumnVisibility,
    getCoreRowModel: getCoreRowModel(),
  })

  return (
    <OpenEpisodeEditorProvider value={setEditing}>
      <TmdbMatchSelectionProvider rows={episodes ?? []}>
        <div
          className={
            query.isPlaceholderData
              ? "opacity-60 transition-opacity duration-200"
              : undefined
          }
        >
          <PageHeader title="Link Episode">
            <Button
              variant={inUserChannelsOnly ? "default" : "outline"}
              onClick={() => {
                setInUserChannelsOnly(!inUserChannelsOnly)
                setPagination({ ...pagination, pageIndex: 0 })
              }}
              title="Switch between every unlinked episode and the ones a user's channel holds"
            >
              {inUserChannelsOnly ? <Users /> : <Globe />}
              {inUserChannelsOnly
                ? "In user channels"
                : "All unlinked episodes"}
            </Button>
            <TmdbLinkMultipleButton />
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
                  rowCount: (query.data?.filtered_count ?? 0) - settledHere,
                  totalRowCount: (query.data?.total_count ?? 0) - settledHere,
                }}
              />
            )}
          </div>
        </div>
      </TmdbMatchSelectionProvider>
      {editing ? (
        <EditEpisode
          episode={editing.episode}
          open
          onOpenChange={(open) => {
            if (!open) setEditing(null)
          }}
        />
      ) : null}
    </OpenEpisodeEditorProvider>
  )
}
