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
import AddSeason from "@/components/Plugin/AddSeason"
import {
  type SeasonTableData,
  seasonColumns,
} from "@/components/Plugin/seasonColumns"
import { Button } from "@/components/ui/button"
import { isLoggedIn } from "@/hooks/useAuth"

interface SeasonsListOutput {
  data: SeasonTableData[]
  count: number
}

function getSeasonsQueryOptions(showKey: string) {
  return {
    queryFn: () =>
      request(OpenAPI, {
        method: "GET",
        url: "/api/v1/shows/{show_id}/seasons",
        path: { show_id: showKey },
      }) as Promise<SeasonsListOutput>,
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
  const { data: seasons } = useSuspenseQuery(getSeasonsQueryOptions(showKey))
  const [columnVisibility, setColumnVisibility] = useState<VisibilityState>({
    key: false,
  })

  const table = useReactTable({
    data: seasons.data,
    columns: seasonColumns,
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
            <h1 className="text-2xl font-bold tracking-tight">Seasons</h1>
            <p className="text-muted-foreground">
              Manage seasons for this show
            </p>
          </div>
        </div>
        <div className="flex gap-2">
          <AddSeason showKey={showKey} />
          <ColumnVisibilityButton table={table} />
        </div>
      </div>
      <DataTable
        columns={seasonColumns}
        data={seasons.data}
        columnVisibility={columnVisibility}
        onColumnVisibilityChange={setColumnVisibility}
      />
    </>
  )
}

function ShowDetailPage() {
  return (
    <div className="flex flex-col gap-6">
      <Suspense fallback={<PendingPlugins />}>
        <SeasonsTableContent />
      </Suspense>
    </div>
  )
}
