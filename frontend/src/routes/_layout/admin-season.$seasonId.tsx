// TODO: Validate
import { useSuspenseQuery } from "@tanstack/react-query"
import { createFileRoute, redirect } from "@tanstack/react-router"
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

interface AdminEpisodeTableData {
  key: string
  name: string | null
  id: string
  season_id: string
  episode_number: number | null
  url: string | null
  description: string | null
  image_url: string | null
  release_date: string | null
  air_date: string | null
  duration: number | null
  sort_order: number | null
  data_timestamp: string | null
  update_at: string | null
}

export const Route = createFileRoute("/_layout/admin-season/$seasonId")({
  component: AdminSeasonDetailPage,
  beforeLoad: async () => {
    const user = await UsersService.readUserMe()
    if (!user.is_superuser) {
      throw redirect({ to: "/" })
    }
  },
  head: () => ({
    meta: [{ title: "Admin Episodes - Stream Channeler" }],
  }),
})

function AdminEpisodesTableContent() {
  const { seasonId } = Route.useParams()
  const queryKey = ["admin-media", "seasons", seasonId, "episodes"]

  const { data: episodes } = useSuspenseQuery({
    queryFn: () =>
      request(OpenAPI, {
        method: "GET",
        url: "/api/v1/admin-media/seasons/{season_id}/episodes",
        path: { season_id: seasonId },
      }) as Promise<AdminEpisodeTableData[]>,
    queryKey,
  })

  const adminEpisodeColumns: ColumnDef<AdminEpisodeTableData>[] = [
    {
      accessorKey: "name",
      header: "Name",
      cell: ({ row }) => (
        <span className="font-medium">
          {row.original.name || `No Name (${row.original.id.split("-")[0]})`}
        </span>
      ),
    },
    {
      accessorKey: "episode_number",
      header: "Episode #",
      cell: ({ row }) => (
        <span className="text-muted-foreground">
          {row.original.episode_number ?? "-"}
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
      accessorKey: "release_date",
      header: "Release Date",
      cell: ({ row }) => (
        <span className="text-muted-foreground text-sm">
          {row.original.release_date ?? "-"}
        </span>
      ),
    },
    {
      accessorKey: "duration",
      header: "Duration",
      cell: ({ row }) => (
        <span className="text-muted-foreground">
          {row.original.duration ?? "-"}
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
            entityType="episodes"
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
    data: episodes,
    columns: adminEpisodeColumns,
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
            <h1 className="text-2xl font-bold tracking-tight">Episodes</h1>
            <p className="text-muted-foreground">
              Episodes for this season (read-only)
            </p>
          </div>
        </div>
        <ColumnVisibilityButton table={table} />
      </div>
      <DataTable
        columns={adminEpisodeColumns}
        data={episodes}
        columnVisibility={columnVisibility}
        onColumnVisibilityChange={setColumnVisibility}
      />
    </>
  )
}

function AdminSeasonDetailPage() {
  return (
    <div className="flex flex-col gap-6">
      <Suspense fallback={<PendingPlugins />}>
        <AdminEpisodesTableContent />
      </Suspense>
    </div>
  )
}
