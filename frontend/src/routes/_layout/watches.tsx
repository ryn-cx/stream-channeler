import {
  keepPreviousData,
  useMutation,
  useQueryClient,
  useSuspenseQuery,
} from "@tanstack/react-query"
import { createFileRoute, Link, redirect } from "@tanstack/react-router"
import type { VisibilityState } from "@tanstack/react-table"
import { getCoreRowModel, useReactTable } from "@tanstack/react-table"
import { RefreshCw, Upload } from "lucide-react"
import { Suspense, useState } from "react"

import { WatchesService } from "@/client"
import { ColumnVisibilityButton } from "@/components/Common/ColumnVisibilityButton"
import { DataTable } from "@/components/Common/DataTable"
import PendingWatches from "@/components/Pending/PendingWatches"
import { Button } from "@/components/ui/button"
import { LoadingButton } from "@/components/ui/loading-button"
import { columns } from "@/components/Watches/columns"
import { isLoggedIn } from "@/hooks/useAuth"
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"

function getWatchesQueryOptions() {
  return {
    queryFn: () => WatchesService.getUserWatches(),
    queryKey: ["watches"],
    placeholderData: keepPreviousData,
  }
}

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

function SyncEpisodeWatchesButton() {
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()

  const syncMutation = useMutation({
    mutationFn: () => WatchesService.syncWatches(),
    onSuccess: (result) => {
      showSuccessToast(result.message)
      queryClient.invalidateQueries({ queryKey: ["watches"] })
    },
    onError: handleError.bind(showErrorToast),
  })

  return (
    <LoadingButton
      loading={syncMutation.isPending}
      onClick={() => syncMutation.mutate()}
      className="mt-2 mb-4"
    >
      <RefreshCw />
      Sync Episode Watches
    </LoadingButton>
  )
}

function ImportWatchesButton() {
  return (
    <Button className="mt-2 mb-4" asChild>
      <Link to="/watches/import">
        <Upload />
        Import
      </Link>
    </Button>
  )
}

function WatchesTableContent() {
  const { data: watches } = useSuspenseQuery(getWatchesQueryOptions())
  const [columnVisibility, setColumnVisibility] = useState<VisibilityState>({
    id: false,
    plugin: false,
  })

  const watchesWithDetails = watches.watches.map((watch) => {
    const episode = watches.episodes[watch.episode_id]
    const season = watches.seasons[episode.season_id]
    const show = watches.shows[season.show_id]
    const source = watches.sources[show.source_id]
    const plugin = watches.plugins[source.plugin_id]
    return { ...watch, episode, season, show, source, plugin }
  })

  const table = useReactTable({
    data: watchesWithDetails,
    columns,
    state: { columnVisibility },
    onColumnVisibilityChange: setColumnVisibility,
    getCoreRowModel: getCoreRowModel(),
  })

  return (
    <>
      {/* flex - Line up text and button on the same row */}
      {/* Vertically center the text */}
      {/* gap-4 - Space between buttons */}
      <div className="flex items-center gap-4">
        <h1 className="text-2xl font-bold">Watches</h1>
        <SyncEpisodeWatchesButton />
        <ImportWatchesButton />
        <ColumnVisibilityButton table={table} />
      </div>
      <DataTable
        columns={columns}
        data={watchesWithDetails}
        columnVisibility={columnVisibility}
        onColumnVisibilityChange={setColumnVisibility}
        sortingStorageKey="watches-sorting"
      />
    </>
  )
}

function WatchesTable() {
  return (
    <Suspense fallback={<PendingWatches />}>
      <WatchesTableContent />
    </Suspense>
  )
}

function Watches() {
  return (
    // px-4 - Border around the table.
    <div className="px-4">
      <WatchesTable />
    </div>
  )
}
