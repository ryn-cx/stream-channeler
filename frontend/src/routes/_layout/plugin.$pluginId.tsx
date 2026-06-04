// TODO: Validate
import { useQuery } from "@tanstack/react-query"
import { createFileRoute, Link, redirect } from "@tanstack/react-router"
import type { VisibilityState } from "@tanstack/react-table"
import { getCoreRowModel, useReactTable } from "@tanstack/react-table"
import { ArrowLeft, Database } from "lucide-react"

import { OpenAPI } from "@/client"
import { request } from "@/client/core/request"
import { ColumnVisibilityButton } from "@/components/Common/ColumnVisibilityButton"
import { DataTable } from "@/components/Common/DataTable"
import { DataTableSkeleton } from "@/components/Common/DataTableSkeleton"
import { EmptyState } from "@/components/Common/EmptyState"
import AddSource from "@/components/Plugin/AddSource"
import {
  type SourceTableData,
  sourceColumns,
} from "@/components/Plugin/sourceColumns"
import { Button } from "@/components/ui/button"
import { isLoggedIn } from "@/hooks/useAuth"
import { usePersistedJsonState } from "@/hooks/usePersistedState"

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
  const { data: sources } = useQuery(getSourcesQueryOptions(pluginId))
  const [columnVisibility, setColumnVisibility] =
    usePersistedJsonState<VisibilityState>("sources-column-visibility", {
      key: false,
      id: false,
    })
  const table = useReactTable({
    data: sources ?? [],
    columns: sourceColumns,
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
          <Button variant="ghost" size="icon" asChild>
            <Link to="/plugins">
              <ArrowLeft />
            </Link>
          </Button>
          <h1 className="text-2xl font-bold tracking-tight">Sources</h1>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <AddSource pluginId={pluginId} />
          <ColumnVisibilityButton table={table} />
        </div>
      </div>
      {!sources ? (
        <div className="px-[4%]">
          <DataTableSkeleton table={table} />
        </div>
      ) : sources.length === 0 ? (
        <EmptyState
          icon={Database}
          title="This plugin has no sources yet"
          description="Add a source to get started"
        />
      ) : (
        <div className="px-[4%]">
          <DataTable
            columns={sourceColumns}
            data={sources}
            columnVisibility={columnVisibility}
            onColumnVisibilityChange={setColumnVisibility}
          />
        </div>
      )}
    </>
  )
}

function PluginDetailPage() {
  return (
    <div className="flex flex-col gap-6">
      <SourcesTableContent />
    </div>
  )
}
