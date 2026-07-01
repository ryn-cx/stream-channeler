// TODO: Validate
import { useQuery } from "@tanstack/react-query"
import { createFileRoute, redirect } from "@tanstack/react-router"
import type { VisibilityState } from "@tanstack/react-table"
import { getCoreRowModel, useReactTable } from "@tanstack/react-table"
import { LayoutGrid, ListMusic, Table as TableIcon } from "lucide-react"

import { SnapshotsService } from "@/client"
import { ColumnVisibilityButton } from "@/components/Common/ColumnVisibilityButton"
import { DataTable } from "@/components/Common/DataTable"
import { EmptyState } from "@/components/Common/EmptyState"
import { PageHeader } from "@/components/Common/PageHeader"
import PendingSnapshots from "@/components/Pending/PendingSnapshots"
import { columns } from "@/components/Snapshots/SnapshotList/columns"
import { SnapshotsBrowse } from "@/components/Snapshots/SnapshotList/SnapshotsBrowse"
import { Button } from "@/components/ui/button"
import { isLoggedIn } from "@/hooks/useAuth"
import {
  usePersistedJsonState,
  usePersistedState,
} from "@/hooks/usePersistedState"

function getSnapshotsQueryOptions() {
  return {
    queryFn: () => SnapshotsService.getSnapshots(),
    queryKey: ["snapshots"],
    refetchOnWindowFocus: false,
    placeholderData: (previousData: any) => previousData,
  }
}

export const Route = createFileRoute("/_layout/snapshots/")({
  component: Snapshots,
  beforeLoad: async () => {
    if (!isLoggedIn()) {
      throw redirect({ to: "/" })
    }
  },
  head: () => ({
    meta: [
      {
        title: "Snapshots - Stream Channeler",
      },
    ],
  }),
})

type ViewMode = "table" | "browse"

function SnapshotsContent() {
  const { data: snapshots, isPlaceholderData } = useQuery(
    getSnapshotsQueryOptions(),
  )
  const [viewMode, setViewMode] = usePersistedState<ViewMode>(
    "snapshots-list-view",
    "browse",
  )

  const [columnVisibility, setColumnVisibility] =
    usePersistedJsonState<VisibilityState>("snapshots-column-visibility", {
      id: false,
    })

  const tableData = snapshots ?? []

  const table = useReactTable({
    data: tableData,
    columns,
    state: {
      columnVisibility,
    },
    onColumnVisibilityChange: setColumnVisibility,
    getCoreRowModel: getCoreRowModel(),
  })

  if (!snapshots) return <PendingSnapshots />

  return (
    <div
      className={
        isPlaceholderData
          ? "opacity-60 transition-opacity duration-200"
          : undefined
      }
    >
      <PageHeader title="Snapshots">
        {viewMode === "browse" ? (
          <Button
            variant="outline"
            onClick={() => setViewMode("table")}
            title="Switch to table view"
            className="my-4"
          >
            <TableIcon />
            Table
          </Button>
        ) : (
          <Button
            variant="outline"
            onClick={() => setViewMode("browse")}
            title="Switch to browse view"
            className="my-4"
          >
            <LayoutGrid />
            Browse
          </Button>
        )}
        {viewMode === "table" && <ColumnVisibilityButton table={table} />}
      </PageHeader>

      {tableData.length === 0 ? (
        <EmptyState
          icon={ListMusic}
          title="You don't have any snapshots yet"
          description="Create a snapshot to get started"
        />
      ) : viewMode === "table" ? (
        <div className="px-[4%]">
          <DataTable
            columns={columns}
            data={tableData}
            columnVisibility={columnVisibility}
            onColumnVisibilityChange={setColumnVisibility}
          />
        </div>
      ) : (
        <SnapshotsBrowse snapshots={tableData} />
      )}
    </div>
  )
}

function Snapshots() {
  return (
    <div className="flex flex-col gap-6">
      <SnapshotsContent />
    </div>
  )
}
