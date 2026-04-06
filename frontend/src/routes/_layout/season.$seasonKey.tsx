// TODO: Validate
import { useSuspenseQuery } from "@tanstack/react-query"
import { createFileRoute, redirect } from "@tanstack/react-router"
import type { VisibilityState } from "@tanstack/react-table"
import { getCoreRowModel, useReactTable } from "@tanstack/react-table"
import { ArrowLeft } from "lucide-react"
import { Suspense, useState } from "react"

import { OpenAPI } from "@/client"
import { request } from "@/client/core/request"
import { ColumnVisibilityButton } from "@/components/Common/ColumnVisibilityButton"
import { DataTable } from "@/components/Common/DataTable"
import PendingPlugins from "@/components/Pending/PendingPlugins"
import AddEpisode from "@/components/Plugin/AddEpisode"
import {
  type EpisodeTableData,
  episodeColumns,
} from "@/components/Plugin/episodeColumns"
import { Button } from "@/components/ui/button"
import { isLoggedIn } from "@/hooks/useAuth"

function getEpisodesQueryOptions(seasonKey: string) {
  return {
    queryFn: () =>
      request(OpenAPI, {
        method: "GET",
        url: "/api/v1/seasons/{season_id}/episodes",
        path: { season_id: seasonKey },
      }) as Promise<EpisodeTableData[]>,
    queryKey: ["seasons", seasonKey, "episodes"],
  }
}

export const Route = createFileRoute("/_layout/season/$seasonKey")({
  component: SeasonDetailPage,
  beforeLoad: async () => {
    if (!isLoggedIn()) {
      throw redirect({ to: "/" })
    }
  },
  head: () => ({
    meta: [{ title: "Season Episodes - Stream Channeler" }],
  }),
})

function EpisodesTableContent() {
  const { seasonKey } = Route.useParams()
  const { data: episodes } = useSuspenseQuery(
    getEpisodesQueryOptions(seasonKey),
  )
  const [columnVisibility, setColumnVisibility] = useState<VisibilityState>({
    key: false,
  })

  const table = useReactTable({
    data: episodes,
    columns: episodeColumns,
    state: {
      columnVisibility,
    },
    onColumnVisibilityChange: setColumnVisibility,
    getCoreRowModel: getCoreRowModel(),
  })

  return (
    <>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button
            variant="ghost"
            size="icon"
            onClick={() => window.history.back()}
          >
            <ArrowLeft />
          </Button>
          <div>
            <h1 className="text-2xl font-bold tracking-tight">Episodes</h1>
            <p className="text-muted-foreground">
              Manage episodes for this season
            </p>
          </div>
        </div>
        <div className="flex gap-2">
          <AddEpisode seasonKey={seasonKey} />
          <ColumnVisibilityButton table={table} />
        </div>
      </div>
      <DataTable
        columns={episodeColumns}
        data={episodes}
        columnVisibility={columnVisibility}
        onColumnVisibilityChange={setColumnVisibility}
      />
    </>
  )
}

function SeasonDetailPage() {
  return (
    <div className="flex flex-col gap-6">
      <Suspense fallback={<PendingPlugins />}>
        <EpisodesTableContent />
      </Suspense>
    </div>
  )
}
