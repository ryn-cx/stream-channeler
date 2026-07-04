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
import { channelColumns } from "./channelColumns"

const ownerScopes = [undefined, "official", "others"] as const

export function ChannelsAdminTable() {
  const results = useQueries({
    queries: ownerScopes.map((owner) => ({
      queryFn: () => ChannelsService.getChannels(owner ? { owner } : {}),
      queryKey: ["admin-channels", owner ?? "mine"],
      refetchOnWindowFocus: false,
    })),
  })
  const isPlaceholderData = results.some((result) => result.isFetching)
  const channels = results.every((result) => result.data)
    ? results.flatMap((result) => result.data ?? [])
    : undefined

  const [columnVisibility, setColumnVisibility] =
    usePersistedJsonState<VisibilityState>(
      "admin-channels-column-visibility",
      {},
    )

  const table = useReactTable({
    data: channels ?? [],
    columns: channelColumns,
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
      <PageHeader title="All Channels">
        <ColumnVisibilityButton table={table} />
      </PageHeader>
      <div className="px-[4%]">
        {!channels ? (
          <DataTableSkeleton table={table} />
        ) : (
          <DataTable
            columns={channelColumns}
            data={channels}
            storageKey="admin-channels"
            columnVisibility={columnVisibility}
            onColumnVisibilityChange={setColumnVisibility}
          />
        )}
      </div>
    </div>
  )
}
