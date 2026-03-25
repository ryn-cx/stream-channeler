// TODO: Validate
import { useQuery } from "@tanstack/react-query"
import { createFileRoute, Link, redirect } from "@tanstack/react-router"
import type { ColumnDef, VisibilityState } from "@tanstack/react-table"
import { getCoreRowModel, useReactTable } from "@tanstack/react-table"
import { useState } from "react"

import { OpenAPI, UsersService } from "@/client"
import { request } from "@/client/core/request"
import TriggerUpdateButton from "@/components/AdminMedia/TriggerUpdateButton"
import { ColumnVisibilityButton } from "@/components/Common/ColumnVisibilityButton"
import { DataTable } from "@/components/Common/DataTable"
import PendingPlugins from "@/components/Pending/PendingPlugins"

interface AdminPluginTableData {
  key: string
  name: string | null
  version: string | null
  id: string
  user_id: string | null
  data_timestamp: string | null
  update_at: string | null
  public: boolean
}

interface AdminPluginsListOutput {
  data: AdminPluginTableData[]
}

const queryKey = ["admin-media", "plugins"]

function getAdminPluginsQueryOptions() {
  return {
    queryFn: () =>
      request(OpenAPI, {
        method: "GET",
        url: "/api/v1/admin-media/plugins",
      }) as Promise<AdminPluginsListOutput>,
    queryKey,
    refetchOnWindowFocus: false,
    placeholderData: (previousData: any) => previousData,
  }
}

const adminPluginColumns: ColumnDef<AdminPluginTableData>[] = [
  {
    accessorKey: "name",
    header: "Name",
    cell: ({ row }) => (
      <Link
        to="/admin-plugin/$pluginId"
        params={{ pluginId: row.original.id }}
        className="font-medium text-primary hover:underline"
      >
        {row.original.name || row.original.key}
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
    accessorFn: (row) => (row.public ? "Public" : "Private"),
    id: "public",
    header: "Visibility",
    cell: ({ row }) => (
      <span className={row.original.public ? "" : "text-muted-foreground"}>
        {row.original.public ? "Public" : "Private"}
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
          entityType="plugins"
          entityId={row.original.id}
          queryKey={queryKey}
        />
      </div>
    ),
  },
]

export const Route = createFileRoute("/_layout/admin-media/")({
  component: AdminMediaPage,
  beforeLoad: async () => {
    const user = await UsersService.readUserMe()
    if (!user.is_superuser) {
      throw redirect({ to: "/" })
    }
  },
  head: () => ({
    meta: [{ title: "Admin Media - Stream Channeler" }],
  }),
})

function AdminPluginsTableContent() {
  const { data: plugins, isPlaceholderData } = useQuery(
    getAdminPluginsQueryOptions(),
  )
  const [columnVisibility, setColumnVisibility] = useState<VisibilityState>({
    key: false,
  })

  const table = useReactTable({
    data: plugins?.data ?? [],
    columns: adminPluginColumns,
    state: { columnVisibility },
    onColumnVisibilityChange: setColumnVisibility,
    getCoreRowModel: getCoreRowModel(),
  })

  if (!plugins) return <PendingPlugins />

  return (
    <div
      className={
        isPlaceholderData
          ? "opacity-60 transition-opacity duration-200"
          : undefined
      }
    >
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Admin Media</h1>
          <p className="text-muted-foreground">
            View all plugins across all users
          </p>
        </div>
        <ColumnVisibilityButton table={table} />
      </div>
      <DataTable
        columns={adminPluginColumns}
        data={plugins.data}
        columnVisibility={columnVisibility}
        onColumnVisibilityChange={setColumnVisibility}
      />
    </div>
  )
}

function AdminMediaPage() {
  return (
    <div className="flex flex-col gap-6">
      <AdminPluginsTableContent />
    </div>
  )
}
