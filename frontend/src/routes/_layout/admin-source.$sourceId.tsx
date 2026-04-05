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

interface AdminShowTableData {
  key: string
  name: string | null
  id: string
  source_id: string
  media_type: string | null
  description: string | null
  url: string | null
  image_url: string | null
  data_timestamp: string | null
  update_at: string | null
}

interface AdminShowsListOutput {
  data: AdminShowTableData[]
}

export const Route = createFileRoute("/_layout/admin-source/$sourceId")({
  component: AdminSourceDetailPage,
  beforeLoad: async () => {
    const user = await UsersService.readUserMe()
    if (!user.is_superuser) {
      throw redirect({ to: "/" })
    }
  },
  head: () => ({
    meta: [{ title: "Admin Shows - Stream Channeler" }],
  }),
})

function AdminShowsTableContent() {
  const { sourceId } = Route.useParams()
  const queryKey = ["admin-media", "sources", sourceId, "shows"]

  const { data: shows } = useSuspenseQuery({
    queryFn: () =>
      request(OpenAPI, {
        method: "GET",
        url: "/api/v1/admin-media/sources/{source_id}/shows",
        path: { source_id: sourceId },
      }) as Promise<AdminShowsListOutput>,
    queryKey,
  })

  const adminShowColumns: ColumnDef<AdminShowTableData>[] = [
    {
      accessorKey: "name",
      header: "Name",
      cell: ({ row }) => (
        <Link
          to="/admin-show/$showId"
          params={{ showId: row.original.id }}
          className="font-medium text-primary hover:underline"
        >
          {row.original.name || `No Name (${row.original.id.split("-")[0]})`}
        </Link>
      ),
    },
    {
      accessorKey: "media_type",
      header: "Media Type",
      cell: ({ row }) => (
        <span className="text-muted-foreground">
          {row.original.media_type ?? "-"}
        </span>
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
            entityType="shows"
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
    data: shows.data,
    columns: adminShowColumns,
    state: { columnVisibility },
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
              Shows for this source (read-only)
            </p>
          </div>
        </div>
        <ColumnVisibilityButton table={table} />
      </div>
      <DataTable
        columns={adminShowColumns}
        data={shows.data}
        columnVisibility={columnVisibility}
        onColumnVisibilityChange={setColumnVisibility}
      />
    </>
  )
}

function AdminSourceDetailPage() {
  return (
    <div className="flex flex-col gap-6">
      <Suspense fallback={<PendingPlugins />}>
        <AdminShowsTableContent />
      </Suspense>
    </div>
  )
}
