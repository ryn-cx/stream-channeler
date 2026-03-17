// TODO: Validate
import { useSuspenseQuery } from "@tanstack/react-query"
import { createFileRoute, Link, redirect } from "@tanstack/react-router"
import type { VisibilityState } from "@tanstack/react-table"
import { getCoreRowModel, useReactTable } from "@tanstack/react-table"
import { Search, Upload } from "lucide-react"
import { Suspense, useState } from "react"

import { WatchesService } from "@/client"
import { ColumnVisibilityButton } from "@/components/Common/ColumnVisibilityButton"
import { DataTable } from "@/components/Common/DataTable"
import PendingWatches from "@/components/Pending/PendingWatches"
import { Button } from "@/components/ui/button"
import { columns } from "@/components/Watches/columns"
import { isLoggedIn } from "@/hooks/useAuth"

function getWatchesQueryOptions() {
  return {
    queryFn: () => WatchesService.getUserWatches(),
    queryKey: ["watches"],
    refetchOnWindowFocus: false,
    refetchOnMount: false,
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

    return {
      ...watch,
      episode,
      season,
      show,
      source,
      plugin,
    }
  })

  const table = useReactTable({
    data: watchesWithDetails,
    columns,
    state: {
      columnVisibility,
    },
    onColumnVisibilityChange: setColumnVisibility,
    getCoreRowModel: getCoreRowModel(),
  })

  if (watches.watches.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center text-center py-12">
        <div className="rounded-full bg-muted p-4 mb-4">
          <Search className="h-8 w-8 text-muted-foreground" />
        </div>
        <h3 className="text-lg font-semibold">
          You don't have any watch history yet
        </h3>
        <p className="text-muted-foreground">
          Add a new watch entry to get started
        </p>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Watches</h1>
          <p className="text-muted-foreground">
            View and manage your watch history
          </p>
        </div>
        <div className="flex gap-2">
          <Button className="my-4" asChild>
            <Link to="/watches/import">
              <Upload className="mr-2" />
              Import
            </Link>
          </Button>
          <ColumnVisibilityButton table={table} />
        </div>
      </div>
      <DataTable
        columns={columns}
        data={watchesWithDetails}
        columnVisibility={columnVisibility}
        onColumnVisibilityChange={setColumnVisibility}
        sortingStorageKey="watches-sorting"
      />
    </div>
  )
}

function Watches() {
  return (
    <Suspense fallback={<PendingWatches />}>
      <WatchesTableContent />
    </Suspense>
  )
}
