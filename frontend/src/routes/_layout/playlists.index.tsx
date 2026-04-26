// TODO: Validate
import { useQuery } from "@tanstack/react-query"
import { createFileRoute, redirect } from "@tanstack/react-router"
import type { VisibilityState } from "@tanstack/react-table"
import { getCoreRowModel, useReactTable } from "@tanstack/react-table"
import { LayoutGrid, Table as TableIcon } from "lucide-react"
import { useState } from "react"

import { PlaylistsService } from "@/client"
import { ColumnVisibilityButton } from "@/components/Common/ColumnVisibilityButton"
import { DataTable } from "@/components/Common/DataTable"
import { columns } from "@/components/Playlists/PlaylistList/columns"
import { PlaylistsBrowse } from "@/components/Playlists/PlaylistList/PlaylistsBrowse"
import { Button } from "@/components/ui/button"
import { isLoggedIn } from "@/hooks/useAuth"
import { usePersistedState } from "@/hooks/usePersistedState"

function getPlaylistsQueryOptions() {
  return {
    queryFn: () => PlaylistsService.getPlaylists(),
    queryKey: ["playlists"],
    refetchOnWindowFocus: false,
    placeholderData: (previousData: any) => previousData,
  }
}

export const Route = createFileRoute("/_layout/playlists/")({
  component: Playlists,
  beforeLoad: async () => {
    if (!isLoggedIn()) {
      throw redirect({ to: "/" })
    }
  },
  head: () => ({
    meta: [
      {
        title: "Playlists - Stream Channeler",
      },
    ],
  }),
})

type ViewMode = "table" | "browse"

function PlaylistsContent() {
  const { data: playlists, isPlaceholderData } = useQuery(
    getPlaylistsQueryOptions(),
  )
  const [viewMode, setViewMode] = usePersistedState<ViewMode>(
    "playlists-list-view",
    "browse",
  )

  const [columnVisibility, setColumnVisibility] = useState<VisibilityState>({
    id: false,
  })

  const tableData = playlists ?? []

  const table = useReactTable({
    data: tableData,
    columns,
    state: {
      columnVisibility,
    },
    onColumnVisibilityChange: setColumnVisibility,
    getCoreRowModel: getCoreRowModel(),
  })

  return (
    <div
      className={
        isPlaceholderData
          ? "opacity-60 transition-opacity duration-200"
          : undefined
      }
    >
      <div className="flex flex-wrap items-center gap-2 px-[4%] pt-4 pb-2">
        <h1 className="text-2xl font-bold tracking-tight mr-2">Playlists</h1>
        {viewMode === "browse" ? (
          <Button
            variant="outline"
            onClick={() => setViewMode("table")}
            title="Switch to table view"
            className="mt-2 mb-4"
          >
            <TableIcon />
            Table
          </Button>
        ) : (
          <Button
            variant="outline"
            onClick={() => setViewMode("browse")}
            title="Switch to browse view"
            className="mt-2 mb-4"
          >
            <LayoutGrid />
            Browse
          </Button>
        )}
        {viewMode === "table" && <ColumnVisibilityButton table={table} />}
      </div>

      {viewMode === "table" ? (
        <div className="px-[4%]">
          <DataTable
            columns={columns}
            data={tableData}
            columnVisibility={columnVisibility}
            onColumnVisibilityChange={setColumnVisibility}
          />
        </div>
      ) : (
        <PlaylistsBrowse playlists={tableData} />
      )}
    </div>
  )
}

function Playlists() {
  return (
    <div className="flex flex-col gap-6">
      <PlaylistsContent />
    </div>
  )
}
