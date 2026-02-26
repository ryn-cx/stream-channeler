// TODO: Validate
import { useSuspenseQuery } from "@tanstack/react-query"
import { createFileRoute, redirect } from "@tanstack/react-router"
import type { VisibilityState } from "@tanstack/react-table"
import { getCoreRowModel, useReactTable } from "@tanstack/react-table"
import { Suspense, useState } from "react"

import { ChannelsService } from "@/client"
import AddChannel from "@/components/Channels/ChannelList/AddChannel"
import { columns } from "@/components/Channels/ChannelList/columns"
import { ColumnVisibilityButton } from "@/components/Common/ColumnVisibilityButton"
import { DataTable } from "@/components/Common/DataTable"
import PendingChannelList from "@/components/Pending/PendingChannelList"
import { isLoggedIn } from "@/hooks/useAuth"

function getChannelsQueryOptions() {
  return {
    queryFn: () => ChannelsService.getChannels(),
    queryKey: ["channels"],
    refetchOnWindowFocus: false,
    refetchOnMount: false,
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

function ChannelsTableContent() {
  const { data: channels } = useSuspenseQuery(getChannelsQueryOptions())

  const [columnVisibility, setColumnVisibility] = useState<VisibilityState>({
    id: false,
  })

  const tableData = channels.data

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
    <>
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Channels</h1>
          <p className="text-muted-foreground">
            Create and manage your channels
          </p>
        </div>
        <div className="flex gap-2">
          <AddChannel />
          <ColumnVisibilityButton table={table} />
        </div>
      </div>

      <DataTable
        columns={columns}
        data={tableData}
        columnVisibility={columnVisibility}
        onColumnVisibilityChange={setColumnVisibility}
      />
    </>
  )
}

function ChannelsTable() {
  return (
    <Suspense fallback={<PendingChannelList />}>
      <ChannelsTableContent />
    </Suspense>
  )
}

function Channels() {
  return (
    <div className="flex flex-col gap-6">
      <ChannelsTable />
    </div>
  )
}
