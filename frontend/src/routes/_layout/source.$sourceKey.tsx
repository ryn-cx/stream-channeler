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
import AddShow from "@/components/Plugin/AddShow"
import {
  type ShowTableData,
  showColumns,
} from "@/components/Plugin/showColumns"
import { Button } from "@/components/ui/button"
import { isLoggedIn } from "@/hooks/useAuth"

interface ShowsListOutput {
  data: ShowTableData[]
  count: number
}

function getShowsQueryOptions(sourceKey: string) {
  return {
    queryFn: () =>
      request(OpenAPI, {
        method: "GET",
        url: "/api/v1/sources/{source_id}/shows",
        path: { source_id: sourceKey },
      }) as Promise<ShowsListOutput>,
    queryKey: ["sources", sourceKey, "shows"],
  }
}

export const Route = createFileRoute("/_layout/source/$sourceKey")({
  component: SourceDetailPage,
  beforeLoad: async () => {
    if (!isLoggedIn()) {
      throw redirect({ to: "/" })
    }
  },
  head: () => ({
    meta: [{ title: "Source Shows - Stream Channeler" }],
  }),
})

function ShowsTableContent() {
  const { sourceKey } = Route.useParams()
  const { data: shows } = useSuspenseQuery(getShowsQueryOptions(sourceKey))
  const [columnVisibility, setColumnVisibility] = useState<VisibilityState>({
    key: false,
  })

  const table = useReactTable({
    data: shows.data,
    columns: showColumns,
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
            <h1 className="text-2xl font-bold tracking-tight">Shows</h1>
            <p className="text-muted-foreground">
              Manage shows for this source
            </p>
          </div>
        </div>
        <div className="flex gap-2">
          <AddShow sourceKey={sourceKey} />
          <ColumnVisibilityButton table={table} />
        </div>
      </div>
      <DataTable
        columns={showColumns}
        data={shows.data}
        columnVisibility={columnVisibility}
        onColumnVisibilityChange={setColumnVisibility}
      />
    </>
  )
}

function SourceDetailPage() {
  return (
    <div className="flex flex-col gap-6">
      <Suspense fallback={<PendingPlugins />}>
        <ShowsTableContent />
      </Suspense>
    </div>
  )
}
