// TODO: Validate
import { useSuspenseQuery } from "@tanstack/react-query"
import { createFileRoute, Link, redirect } from "@tanstack/react-router"
import type { VisibilityState } from "@tanstack/react-table"
import { getCoreRowModel, useReactTable } from "@tanstack/react-table"
import { ArrowLeft } from "lucide-react"
import { Suspense, useState } from "react"

import { OpenAPI } from "@/client"
import { request } from "@/client/core/request"
import { ColumnVisibilityButton } from "@/components/Common/ColumnVisibilityButton"
import { DataTable } from "@/components/Common/DataTable"
import PendingPlugins from "@/components/Pending/PendingPlugins"
import AddSource from "@/components/Plugin/AddSource"
import {
  type SourceTableData,
  sourceColumns,
} from "@/components/Plugin/sourceColumns"
import { Button } from "@/components/ui/button"
import { isLoggedIn } from "@/hooks/useAuth"

function getSourcesQueryOptions(pluginId: string) {
  return {
    queryFn: () =>
      request(OpenAPI, {
        method: "GET",
        url: "/api/v1/plugins/{plugin_id}/sources",
        path: { plugin_id: pluginId },
      }) as Promise<SourceTableData[]>,
    queryKey: ["plugins", pluginId, "sources"],
  }
}

export const Route = createFileRoute("/_layout/plugin/$pluginId")({
  component: PluginDetailPage,
  beforeLoad: async () => {
    if (!isLoggedIn()) {
      throw redirect({ to: "/" })
    }
  },
  head: () => ({
    meta: [{ title: "Plugin Sources - Stream Channeler" }],
  }),
})

function SourcesTableContent() {
  const { pluginId } = Route.useParams()
  const { data: sources } = useSuspenseQuery(getSourcesQueryOptions(pluginId))
  const [columnVisibility, setColumnVisibility] = useState<VisibilityState>({
    key: false,
    id: false,
  })
  const table = useReactTable({
    data: sources,
    columns: sourceColumns,
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
          <Button variant="ghost" size="icon" asChild>
            <Link to="/plugins">
              <ArrowLeft />
            </Link>
          </Button>
          <div>
            <h1 className="text-2xl font-bold tracking-tight">Sources</h1>
            <p className="text-muted-foreground">
              Manage sources for this plugin
            </p>
          </div>
        </div>
        <div className="flex gap-2">
          <AddSource pluginId={pluginId} />
          <ColumnVisibilityButton table={table} />
        </div>
      </div>
      <DataTable
        columns={sourceColumns}
        data={sources}
        columnVisibility={columnVisibility}
        onColumnVisibilityChange={setColumnVisibility}
      />
    </>
  )
}

function PluginDetailPage() {
  return (
    <div className="flex flex-col gap-6">
      <Suspense fallback={<PendingPlugins />}>
        <SourcesTableContent />
      </Suspense>
    </div>
  )
}
