// TODO: Validate
import { useQuery } from "@tanstack/react-query"
import { createFileRoute, redirect } from "@tanstack/react-router"
import type { VisibilityState } from "@tanstack/react-table"
import { getCoreRowModel, useReactTable } from "@tanstack/react-table"
import { ArrowLeft, Film } from "lucide-react"

import { OpenAPI } from "@/client"
import { request } from "@/client/core/request"
import { ColumnVisibilityButton } from "@/components/Common/ColumnVisibilityButton"
import { DataTable } from "@/components/Common/DataTable"
import { DataTableSkeleton } from "@/components/Common/DataTableSkeleton"
import { EmptyState } from "@/components/Common/EmptyState"
import AddEpisode from "@/components/Plugin/AddEpisode"
import {
  type EpisodeTableData,
  episodeColumns,
} from "@/components/Plugin/episodeColumns"
import { Button } from "@/components/ui/button"
import { isLoggedIn } from "@/hooks/useAuth"
import { usePersistedJsonState } from "@/hooks/usePersistedState"

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
  const { data: episodes } = useQuery(getEpisodesQueryOptions(seasonKey))
  const [columnVisibility, setColumnVisibility] =
    usePersistedJsonState<VisibilityState>("episodes-column-visibility", {
      key: false,
      id: false,
    })

  const table = useReactTable({
    data: episodes ?? [],
    columns: episodeColumns,
    state: {
      columnVisibility,
    },
    onColumnVisibilityChange: setColumnVisibility,
    getCoreRowModel: getCoreRowModel(),
  })

  return (
    <>
      <div className="flex flex-wrap items-center justify-between gap-2 px-[4%] pt-4 pb-2">
        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="icon"
            onClick={() => window.history.back()}
          >
            <ArrowLeft />
          </Button>
          <h1 className="text-2xl font-bold tracking-tight">Episodes</h1>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <AddEpisode seasonKey={seasonKey} />
          <ColumnVisibilityButton table={table} />
        </div>
      </div>
      {!episodes ? (
        <div className="px-[4%]">
          <DataTableSkeleton table={table} />
        </div>
      ) : episodes.length === 0 ? (
        <EmptyState
          icon={Film}
          title="This season has no episodes yet"
          description="Add an episode to get started"
        />
      ) : (
        <div className="px-[4%]">
          <DataTable
            columns={episodeColumns}
            data={episodes}
            columnVisibility={columnVisibility}
            onColumnVisibilityChange={setColumnVisibility}
          />
        </div>
      )}
    </>
  )
}

function SeasonDetailPage() {
  return (
    <div className="flex flex-col gap-6">
      <EpisodesTableContent />
    </div>
  )
}
