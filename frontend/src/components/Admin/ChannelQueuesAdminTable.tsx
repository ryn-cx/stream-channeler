// TODO: Validate
import { useQueries } from "@tanstack/react-query"
import type { VisibilityState } from "@tanstack/react-table"
import { getCoreRowModel, useReactTable } from "@tanstack/react-table"

import { ChannelsService } from "@/client"
import { ColumnVisibilityButton } from "@/components/Common/ColumnVisibilityButton"
import { DataTable } from "@/components/Common/DataTable"
import { DataTableSkeleton } from "@/components/Common/DataTableSkeleton"
import { PageHeader } from "@/components/Common/PageHeader"
import { usePersistedJsonState } from "@/hooks/usePersistedState"
import { channelQueueColumns } from "./channelQueueColumns"

const ownerScopes = [undefined, "official", "others"] as const

export function ChannelQueuesAdminTable() {
  const results = useQueries({
    queries: ownerScopes.map((owner) => ({
      queryFn: () =>
        ChannelsService.getAllChannelQueues(owner ? { owner } : {}),
      queryKey: ["admin-channel-queues", owner ?? "mine"],
      refetchOnWindowFocus: false,
    })),
  })
  const isPlaceholderData = results.some((result) => result.isFetching)
  const entries = results.every((result) => result.data)
    ? results.flatMap((result) => result.data ?? [])
    : undefined

  const [columnVisibility, setColumnVisibility] =
    usePersistedJsonState<VisibilityState>(
      "admin-channel-queues-column-visibility",
      {},
    )

  const table = useReactTable({
    data: entries ?? [],
    columns: channelQueueColumns,
    state: { columnVisibility },
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
      <PageHeader title="All Channel Queues">
        <ColumnVisibilityButton table={table} />
      </PageHeader>
      <div className="px-[4%]">
        {!entries ? (
          <DataTableSkeleton table={table} />
        ) : (
          <DataTable
            columns={channelQueueColumns}
            data={entries}
            storageKey="admin-channel-queues"
            columnVisibility={columnVisibility}
            onColumnVisibilityChange={setColumnVisibility}
          />
        )}
      </div>
    </div>
  )
}
