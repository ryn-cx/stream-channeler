// TODO: Validate
import { useQuery } from "@tanstack/react-query"
import { createFileRoute, redirect } from "@tanstack/react-router"
import type { VisibilityState } from "@tanstack/react-table"
import { getCoreRowModel, useReactTable } from "@tanstack/react-table"
import { LayoutGrid, Table as TableIcon } from "lucide-react"
import { useState } from "react"
import { ChannelsService } from "@/client"
import AddChannel from "@/components/Channels/ChannelList/AddChannel"
import { ChannelsBrowse } from "@/components/Channels/ChannelList/ChannelsBrowse"
import { columns } from "@/components/Channels/ChannelList/columns"
import { ColumnVisibilityButton } from "@/components/Common/ColumnVisibilityButton"
import { DataTable } from "@/components/Common/DataTable"
import PendingChannelList from "@/components/Pending/PendingChannelList"
import { Button } from "@/components/ui/button"
import { ButtonGroup } from "@/components/ui/button-group"
import { isLoggedIn } from "@/hooks/useAuth"
import { usePersistedState } from "@/hooks/usePersistedState"

function getChannelsQueryOptions() {
  return {
    queryFn: () => ChannelsService.getUserChannels(),
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

  const [columnVisibility, setColumnVisibility] = useState<VisibilityState>({
    id: false,
  })

  const tableData = channels?.data ?? []

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
      <div className="flex flex-wrap items-center gap-2 px-[4%] pt-4 pb-2">
        <h1 className="text-2xl font-bold tracking-tight mr-2">Channels</h1>
        <ButtonGroup>
          <Button
            variant={viewMode === "browse" ? "default" : "outline"}
            onClick={() => setViewMode("browse")}
            title="Browse view"
            className="mt-2 mb-4"
          >
            <LayoutGrid />
            Browse
          </Button>
          <Button
            variant={viewMode === "table" ? "default" : "outline"}
            onClick={() => setViewMode("table")}
            title="Table view"
            className="mt-2 mb-4"
          >
            <TableIcon />
            Table
          </Button>
        </ButtonGroup>
        <AddChannel />
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
