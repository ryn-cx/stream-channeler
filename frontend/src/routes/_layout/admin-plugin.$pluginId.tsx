// TODO: Validate
import { useSuspenseQuery } from "@tanstack/react-query"
import { createFileRoute, Link, redirect } from "@tanstack/react-router"
import type { ColumnDef, VisibilityState } from "@tanstack/react-table"
import { getCoreRowModel, useReactTable } from "@tanstack/react-table"
import { ArrowLeft } from "lucide-react"
import { Suspense, useState } from "react"

import { OpenAPI, UsersService } from "@/client"
import { request } from "@/client/core/request"
import TriggerUpdateButton from "@/components/AdminMedia/TriggerUpdateButton"
import { ColumnVisibilityButton } from "@/components/Common/ColumnVisibilityButton"
import { DataTable } from "@/components/Common/DataTable"
import PendingPlugins from "@/components/Pending/PendingPlugins"
import { Button } from "@/components/ui/button"

interface AdminSourceTableData {
  key: string
  name: string | null
  id: string
  plugin_id: string
  favicon_url: string | null
  image_url: string | null
  data_timestamp: string | null
  update_at: string | null
}

interface AdminSourcesListOutput {
  data: AdminSourceTableData[]
}

export const Route = createFileRoute("/_layout/admin-plugin/$pluginId")({
  component: AdminPluginDetailPage,
  beforeLoad: async () => {
    const user = await UsersService.readUserMe()
    if (!user.is_superuser) {
      throw redirect({ to: "/" })
    }
  },
  head: () => ({
    meta: [{ title: "Admin Sources - Stream Channeler" }],
  }),
})

function AdminSourcesTableContent() {
  const { pluginId } = Route.useParams()
  const queryKey = ["admin-media", "plugins", pluginId, "sources"]

  const { data: sources } = useSuspenseQuery({
    queryFn: () =>
      request(OpenAPI, {
        method: "GET",
        url: "/api/v1/admin-media/plugins/{plugin_id}/sources",
        path: { plugin_id: pluginId },
      }) as Promise<AdminSourcesListOutput>,
    queryKey,
  })

  const adminSourceColumns: ColumnDef<AdminSourceTableData>[] = [
    {
      accessorKey: "name",
      header: "Name",
      cell: ({ row }) => (
        <Link
          to="/admin-source/$sourceId"
          params={{ sourceId: row.original.id }}
          className="font-medium text-primary hover:underline"
        >
          {row.original.name || `No Name (${row.original.id.split("-")[0]})`}
        </Link>
      ),
    },
    {
      accessorKey: "data_timestamp",
      header: "Data Timestamp",
      cell: ({ row }) => (
        <span className="text-muted-foreground text-sm">
          {row.original.data_timestamp
            ? new Date(row.original.data_timestamp).toLocaleString()
            : "-"}
        </span>
      ),
    },
    {
      accessorKey: "update_at",
      header: "Update At",
      cell: ({ row }) => (
        <span className="text-muted-foreground text-sm">
          {row.original.update_at
            ? new Date(row.original.update_at).toLocaleString()
            : "-"}
        </span>
      ),
    },
    {
      accessorKey: "key",
      header: "Key",
      cell: ({ row }) => (
        <span className="text-muted-foreground font-mono text-sm">
          {row.original.key}
        </span>
      ),
    },
    {
      id: "actions",
      header: () => <span className="sr-only">Actions</span>,
      enableHiding: false,
      cell: ({ row }) => (
        <div className="flex justify-end">
          <TriggerUpdateButton
            entityType="sources"
            entityId={row.original.id}
            queryKey={queryKey}
          />
        </div>
      ),
    },
  ]

  const [columnVisibility, setColumnVisibility] = useState<VisibilityState>({
    key: false,
  })

  const table = useReactTable({
    data: sources.data,
    columns: adminSourceColumns,
    state: { columnVisibility },
    onColumnVisibilityChange: setColumnVisibility,
    getCoreRowModel: getCoreRowModel(),
  })

  return (
    <>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" asChild>
            <Link to="/admin-media">
              <ArrowLeft />
            </Link>
          </Button>
          <div>
            <h1 className="text-2xl font-bold tracking-tight">Sources</h1>
            <p className="text-muted-foreground">
              Sources for this plugin (read-only)
            </p>
          </div>
        </div>
        <ColumnVisibilityButton table={table} />
      </div>
      <DataTable
        columns={adminSourceColumns}
        data={sources.data}
        columnVisibility={columnVisibility}
        onColumnVisibilityChange={setColumnVisibility}
      />
    </>
  )
}

function AdminPluginDetailPage() {
  return (
    <div className="flex flex-col gap-6">
      <Suspense fallback={<PendingPlugins />}>
        <AdminSourcesTableContent />
      </Suspense>
    </div>
  )
}
