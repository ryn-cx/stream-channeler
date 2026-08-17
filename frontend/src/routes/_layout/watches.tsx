// TODO: Validate
import { keepPreviousData, useMutation, useQuery } from "@tanstack/react-query"
import { createFileRoute, Link, redirect } from "@tanstack/react-router"
import type {
  ColumnFiltersState,
  PaginationState,
  SortingState,
  VisibilityState,
} from "@tanstack/react-table"
import { getCoreRowModel, useReactTable } from "@tanstack/react-table"
import { Download, Eye, Upload } from "lucide-react"
import { useState } from "react"

import { WatchesService } from "@/client"
import { ColumnVisibilityButton } from "@/components/Common/ColumnVisibilityButton"
import { DataTable, serializeTableQuery } from "@/components/Common/DataTable"
import { DataTableSkeleton } from "@/components/Common/DataTableSkeleton"
import { EmptyState } from "@/components/Common/EmptyState"
import { PageHeader } from "@/components/Common/PageHeader"
import { Button } from "@/components/ui/button"
import { LoadingButton } from "@/components/ui/loading-button"
import { columns, type WatchWithDetails } from "@/components/Watches/columns"
import { isLoggedIn } from "@/hooks/useAuth"
import useCustomToast from "@/hooks/useCustomToast"
import { usePersistedJsonState } from "@/hooks/usePersistedState"
import { handleError } from "@/utils"

export const Route = createFileRoute("/_layout/watches")({
  component: Watches,
  beforeLoad: async () => {
    if (!isLoggedIn()) {
      throw redirect({ to: "/" })
    }
  },
  head: () => ({
    meta: [
      {
        title: "Watches - Stream Channeler",
      },
    ],
  }),
})

// TODO: Validate
function ImportWatchesButton() {
  return (
    <Button asChild>
      <Link to="/watches/import">
        <Upload />
        Import
      </Link>
    </Button>
  )
}

// The file holds only what re-importing needs, so it is downloaded straight from
// the response rather than being built from the table's own rows.
// TODO: Validate
function ExportWatchesButton() {
  const { showSuccessToast, showErrorToast } = useCustomToast()

  const mutation = useMutation({
    mutationFn: () => WatchesService.exportWatchHistory(),
    onSuccess: (entries) => {
      const url = URL.createObjectURL(
        new Blob([JSON.stringify(entries, null, 2)], {
          type: "application/json",
        }),
      )
      const link = document.createElement("a")
      link.href = url
      link.download = "stream-channeler-watches.json"
      link.click()
      URL.revokeObjectURL(url)
      showSuccessToast(`Exported ${entries.length} watches`)
    },
    onError: handleError.bind(showErrorToast),
  })

  return (
    <LoadingButton
      variant="outline"
      onClick={() => mutation.mutate()}
      loading={mutation.isPending}
    >
      <Download />
      Export
    </LoadingButton>
  )
}

// TODO: Validate
function WatchesTableContent() {
  const [pagination, setPagination] = useState<PaginationState>({
    pageIndex: 0,
    pageSize: 10,
  })
  const [sortOptions, setSortOptions] = useState<SortingState>([])
  const [filterOptions, setFilterOptions] = useState<ColumnFiltersState>([])
  const [columnVisibility, setColumnVisibility] =
    usePersistedJsonState<VisibilityState>("watches-column-visibility", {
      id: false,
      plugin: false,
    })

  const offset = pagination.pageIndex * pagination.pageSize
  const limit = pagination.pageSize
  const { data: watches, isPlaceholderData } = useQuery({
    queryKey: ["watches", pagination, sortOptions, filterOptions],
    queryFn: () =>
      WatchesService.getWatches({
        offset,
        limit,
        ...serializeTableQuery(
          { offset, limit, sortOptions, filterOptions },
          columns,
        ),
      }),
    placeholderData: keepPreviousData,
  })

  // A watch names the episode itself, and the listing carries one visible
  // non-canonical row
  // of each, so that is what the rest of the row is read from. A watch whose
  // episode has no non-canonical row the viewer can see has no row to show.
  const watchesWithDetails: WatchWithDetails[] = watches
    ? watches.watches.flatMap((watch) => {
        const episode = watch.canonical_episode_id
          ? watches.episodes[watch.canonical_episode_id]
          : undefined
        if (!episode) return []
        const season = watches.seasons[episode.season_id]
        const show = watches.shows[season.show_id]
        const source = watches.sources[show.source_id]
        const plugin = watches.plugins[source.plugin_id]
        return [{ ...watch, episode, season, show, source, plugin }]
      })
    : []

  const isServer = watches?.is_server_side ?? false

  const table = useReactTable({
    data: watchesWithDetails,
    columns,
    state: { columnVisibility },
    onColumnVisibilityChange: setColumnVisibility,
    getCoreRowModel: getCoreRowModel(),
  })

  return (
    <>
      <PageHeader title="Watches">
        <ExportWatchesButton />
        <ImportWatchesButton />
        <ColumnVisibilityButton table={table} />
      </PageHeader>
      {!watches ? (
        <div className="px-[4%]">
          <DataTableSkeleton table={table} />
        </div>
      ) : !isServer && watchesWithDetails.length === 0 ? (
        <EmptyState
          icon={Eye}
          title="You don't have any watches yet"
          description="Sync or import watches to get started"
        />
      ) : (
        <div
          className={
            isPlaceholderData
              ? "px-[4%] opacity-60 transition-opacity duration-200"
              : "px-[4%]"
          }
        >
          <DataTable
            columns={columns}
            data={watchesWithDetails}
            columnVisibility={columnVisibility}
            onColumnVisibilityChange={setColumnVisibility}
            storageKey="watches"
            serverSide={
              isServer
                ? {
                    pagination,
                    sortOptions,
                    filterOptions,
                    onPaginationChange: setPagination,
                    onSortOptionsChange: setSortOptions,
                    onFilterOptionsChange: setFilterOptions,
                    rowCount: watches.filtered_count ?? 0,
                    totalRowCount: watches.total_count ?? 0,
                  }
                : undefined
            }
          />
        </div>
      )}
    </>
  )
}

// TODO: Validate
function Watches() {
  return (
    <div className="flex flex-col gap-6">
      <WatchesTableContent />
    </div>
  )
}
