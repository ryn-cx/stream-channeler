// TODO: Validate
import { useSuspenseQuery } from "@tanstack/react-query"
import { createFileRoute, Link, redirect } from "@tanstack/react-router"
import type { ColumnDef, VisibilityState } from "@tanstack/react-table"
import { getCoreRowModel, useReactTable } from "@tanstack/react-table"
import { ArrowLeft } from "lucide-react"
import { Suspense, useState } from "react"

import { OpenAPI, UsersService } from "@/client"
import { request } from "@/client/core/request"
import ForceUpdateButton from "@/components/AdminMedia/ForceUpdateButton"
import { ColumnVisibilityButton } from "@/components/Common/ColumnVisibilityButton"
import { DataTable } from "@/components/Common/DataTable"
import PendingPlugins from "@/components/Pending/PendingPlugins"
import { Button } from "@/components/ui/button"

interface AdminSeasonTableData {
  key: string
  name: string | null
  id: string
  show_id: string
  season_number: number | null
  url: string | null
  image_url: string | null
  sort_order: number | null
  data_timestamp: string | null
  update_at: string | null
}

export const Route = createFileRoute("/_layout/admin-show/$showId")({
  component: AdminShowDetailPage,
  beforeLoad: async () => {
    const user = await UsersService.readUserMe()
    if (!user.is_superuser) {
      throw redirect({ to: "/" })
    }
  },
  head: () => ({
    meta: [{ title: "Admin Seasons - Stream Channeler" }],
  }),
})

function AdminSeasonsTableContent() {
  const { showId } = Route.useParams()
  const queryKey = ["admin-media", "shows", showId, "seasons"]

  const { data: seasons } = useSuspenseQuery({
    queryFn: () =>
      request(OpenAPI, {
        method: "GET",
        url: "/api/v1/admin-media/shows/{show_id}/seasons",
        path: { show_id: showId },
      }) as Promise<AdminSeasonTableData[]>,
    queryKey,
  })

  const adminSeasonColumns: ColumnDef<AdminSeasonTableData>[] = [
    {
      accessorKey: "name",
      header: "Name",
      cell: ({ row }) => (
        <Link
          to="/admin-season/$seasonId"
          params={{ seasonId: row.original.id }}
          className="font-medium text-primary hover:underline"
        >
          {row.original.name || `No Name (${row.original.id.split("-")[0]})`}
        </Link>
      ),
    },
    {
      accessorKey: "season_number",
      header: "Season #",
      cell: ({ row }) => (
        <span className="text-muted-foreground">
          {row.original.season_number ?? "-"}
        </span>
      ),
    },
    {
      accessorKey: "sort_order",
      header: "Sort Order",
      cell: ({ row }) => (
        <span className="text-muted-foreground">
          {row.original.sort_order ?? "-"}
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
          <ForceUpdateButton
            entityType="seasons"
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
    data: seasons,
    columns: adminSeasonColumns,
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
            <h1 className="text-2xl font-bold tracking-tight">Seasons</h1>
            <p className="text-muted-foreground">
              Seasons for this show (read-only)
            </p>
          </div>
        </div>
        <ColumnVisibilityButton table={table} />
      </div>
      <DataTable
        columns={adminSeasonColumns}
        data={seasons}
        columnVisibility={columnVisibility}
        onColumnVisibilityChange={setColumnVisibility}
      />
    </>
  )
}

function AdminShowDetailPage() {
  return (
    <div className="flex flex-col gap-6">
      <Suspense fallback={<PendingPlugins />}>
        <AdminSeasonsTableContent />
      </Suspense>
    </div>
  )
}
