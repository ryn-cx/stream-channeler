// TODO: Validate
import { useQuery } from "@tanstack/react-query"
import { createFileRoute, redirect } from "@tanstack/react-router"
import type { VisibilityState } from "@tanstack/react-table"
import { getCoreRowModel, useReactTable } from "@tanstack/react-table"
import { ArrowLeft, Layers } from "lucide-react"

import { OpenAPI } from "@/client"
import { request } from "@/client/core/request"
import { ColumnVisibilityButton } from "@/components/Common/ColumnVisibilityButton"
import { DataTable } from "@/components/Common/DataTable"
import { DataTableSkeleton } from "@/components/Common/DataTableSkeleton"
import { EmptyState } from "@/components/Common/EmptyState"
import AddSeason from "@/components/Plugin/AddSeason"
import {
  type SeasonTableData,
  seasonColumns,
} from "@/components/Plugin/seasonColumns"
import { Button } from "@/components/ui/button"
import { isLoggedIn } from "@/hooks/useAuth"
import { usePersistedJsonState } from "@/hooks/usePersistedState"

function getSeasonsQueryOptions(showKey: string) {
  return {
    queryFn: () =>
      request(OpenAPI, {
        method: "GET",
        url: "/api/v1/shows/{show_id}/seasons",
        path: { show_id: showKey },
      }) as Promise<SeasonTableData[]>,
    queryKey: ["shows", showKey, "seasons"],
  }
}

export const Route = createFileRoute("/_layout/show/$showKey")({
  component: ShowDetailPage,
  beforeLoad: async () => {
    if (!isLoggedIn()) {
      throw redirect({ to: "/" })
    }
  },
  head: () => ({
    meta: [{ title: "Show Seasons - Stream Channeler" }],
  }),
})

function SeasonsTableContent() {
  const { showKey } = Route.useParams()
  const { data: seasons } = useQuery(getSeasonsQueryOptions(showKey))
  const [columnVisibility, setColumnVisibility] =
    usePersistedJsonState<VisibilityState>("seasons-column-visibility", {
      key: false,
      id: false,
    })

  const table = useReactTable({
    data: seasons ?? [],
    columns: seasonColumns,
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
          <h1 className="text-2xl font-bold tracking-tight">Seasons</h1>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <AddSeason showKey={showKey} />
          <ColumnVisibilityButton table={table} />
        </div>
      </div>
      {!seasons ? (
        <div className="px-[4%]">
          <DataTableSkeleton table={table} />
        </div>
      ) : seasons.length === 0 ? (
        <EmptyState
          icon={Layers}
          title="This show has no seasons yet"
          description="Add a season to get started"
        />
      ) : (
        <div className="px-[4%]">
          <DataTable
            columns={seasonColumns}
            data={seasons}
            columnVisibility={columnVisibility}
            onColumnVisibilityChange={setColumnVisibility}
          />
        </div>
      )}
    </>
  )
}

function ShowDetailPage() {
  return (
    <div className="flex flex-col gap-6">
      <SeasonsTableContent />
    </div>
  )
}
