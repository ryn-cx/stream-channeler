// TODO: Validate
import { useSuspenseQuery } from "@tanstack/react-query"
import { createFileRoute, redirect } from "@tanstack/react-router"
import type { VisibilityState } from "@tanstack/react-table"
import { getCoreRowModel, useReactTable } from "@tanstack/react-table"
import { Suspense, useState } from "react"

import { OpenAPI } from "@/client"
import { request } from "@/client/core/request"
import { ColumnVisibilityButton } from "@/components/Common/ColumnVisibilityButton"
import { DataTable } from "@/components/Common/DataTable"
import PendingPlugins from "@/components/Pending/PendingPlugins"
import AddPlugin from "@/components/Plugin/AddPlugin"
import { columns, type PluginTableData } from "@/components/Plugin/columns"
import { isLoggedIn } from "@/hooks/useAuth"

interface PluginsListOutput {
  data: PluginTableData[]
  count: number
}

function getPluginsQueryOptions() {
  return {
    queryFn: () =>
      request(OpenAPI, {
        method: "GET",
        url: "/api/v1/plugins",
      }) as Promise<PluginsListOutput>,
    queryKey: ["plugins"],
  }
}

export const Route = createFileRoute("/_layout/plugin/")({
  component: PluginPage,
  beforeLoad: async () => {
    if (!isLoggedIn()) {
      throw redirect({ to: "/" })
    }
  },
  head: () => ({
    meta: [{ title: "Plugins - Stream Channeler" }],
  }),
})

function PluginsTableContent() {
  const { data: plugins } = useSuspenseQuery(getPluginsQueryOptions())
  const [columnVisibility, setColumnVisibility] = useState<VisibilityState>({
    key: false,
  })

  const table = useReactTable({
    data: plugins.data,
    columns,
    state: {
      columnVisibility,
    },
    onColumnVisibilityChange: setColumnVisibility,
    getCoreRowModel: getCoreRowModel(),
  })

  return (
    <>
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Plugins</h1>
          <p className="text-muted-foreground">Manage your plugins</p>
        </div>
        <div className="flex gap-2">
          <AddPlugin />
          <ColumnVisibilityButton table={table} />
        </div>
      </div>
      <DataTable
        columns={columns}
        data={plugins.data}
        columnVisibility={columnVisibility}
        onColumnVisibilityChange={setColumnVisibility}
      />
    </>
  )
}

function PluginPage() {
  return (
    <div className="flex flex-col gap-6">
      <Suspense fallback={<PendingPlugins />}>
        <PluginsTableContent />
      </Suspense>
    </div>
  )
}
