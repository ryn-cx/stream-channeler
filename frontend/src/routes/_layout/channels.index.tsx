// TODO: Validate
import { useQuery } from "@tanstack/react-query"
import { createFileRoute, redirect } from "@tanstack/react-router"
import type { VisibilityState } from "@tanstack/react-table"
import { getCoreRowModel, useReactTable } from "@tanstack/react-table"
import { LayoutGrid, Table as TableIcon, Tv } from "lucide-react"
import { ChannelsService } from "@/client"
import AddChannel from "@/components/Channels/ChannelList/AddChannel"
import { BulkImport } from "@/components/Channels/ChannelList/BulkImport"
import { ChannelsBrowse } from "@/components/Channels/ChannelList/ChannelsBrowse"
import { columns } from "@/components/Channels/ChannelList/columns"
import { ColumnVisibilityButton } from "@/components/Common/ColumnVisibilityButton"
import { DataTable } from "@/components/Common/DataTable"
import { EmptyState } from "@/components/Common/EmptyState"
import { PageHeader } from "@/components/Common/PageHeader"
import PendingChannelList from "@/components/Pending/PendingChannelList"
import { Button } from "@/components/ui/button"
import { isLoggedIn } from "@/hooks/useAuth"
import {
  usePersistedJsonState,
  usePersistedState,
} from "@/hooks/usePersistedState"

function getChannelsQueryOptions() {
  return {
    queryFn: () => ChannelsService.getChannels(),
    queryKey: ["channels"],
    refetchOnWindowFocus: false,
    placeholderData: (previousData: any) => previousData,
  }
}

export const Route = createFileRoute("/_layout/channels/")({
  component: Channels,
  beforeLoad: async () => {
    if (!isLoggedIn()) {
      throw redirect({ to: "/" })
    }
  },
  head: () => ({
    meta: [
      {
        title: "Channels - Stream Channeler",
      },
    ],
  }),
})

type ViewMode = "table" | "browse"

function ChannelsContent() {
  const { data: channels, isPlaceholderData } = useQuery(
    getChannelsQueryOptions(),
  )
  const [viewMode, setViewMode] = usePersistedState<ViewMode>(
    "channels-list-view",
    "browse",
  )

  const [columnVisibility, setColumnVisibility] =
    usePersistedJsonState<VisibilityState>("channels-column-visibility", {
      id: false,
    })

  const tableData = channels ?? []

  const table = useReactTable({
    data: tableData,
    columns,
    state: {
      columnVisibility,
    },
    onColumnVisibilityChange: setColumnVisibility,
    getCoreRowModel: getCoreRowModel(),
  })

  if (!channels) return <PendingChannelList />

  return (
    <div
      className={
        isPlaceholderData
          ? "opacity-60 transition-opacity duration-200"
          : undefined
      }
    >
      <PageHeader title="Channels">
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
        <AddChannel />
        <BulkImport />
        {viewMode === "table" && <ColumnVisibilityButton table={table} />}
      </PageHeader>

      {tableData.length === 0 ? (
        <EmptyState
          icon={Tv}
          title="You don't have any channels yet"
          description="Create a channel to get started"
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
        <ChannelsBrowse channels={tableData} />
      )}
    </div>
  )
}

function Channels() {
  return (
    <div className="flex flex-col gap-6">
      <ChannelsContent />
    </div>
  )
}
