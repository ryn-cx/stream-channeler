// TODO: Validate
import { useQuery } from "@tanstack/react-query"
import type { VisibilityState } from "@tanstack/react-table"
import { getCoreRowModel, useReactTable } from "@tanstack/react-table"

import { EpisodesService } from "@/client"
import { ColumnVisibilityButton } from "@/components/Common/ColumnVisibilityButton"
import { DataTable } from "@/components/Common/DataTable"
import { DataTableSkeleton } from "@/components/Common/DataTableSkeleton"
import { PageHeader } from "@/components/Common/PageHeader"
import { usePersistedJsonState } from "@/hooks/usePersistedState"
import { tmdbMatchColumns } from "./tmdbMatchColumns"
import { UNLOCKED_EPISODES_QUERY_KEY } from "./unlockedEpisodesQuery"

const STORAGE_KEY = "admin-unlocked-episodes"

// TODO: Validate
export function UnlockedEpisodesAdminTable() {
  const [columnVisibility, setColumnVisibility] =
    usePersistedJsonState<VisibilityState>(`${STORAGE_KEY}-visibility`, {})

  const { data: episodes } = useQuery({
    queryKey: UNLOCKED_EPISODES_QUERY_KEY,
    queryFn: () => EpisodesService.adminGetUnlockedEpisodes({ limit: 1000 }),
  })

  const table = useReactTable({
    data: episodes ?? [],
    columns: tmdbMatchColumns,
    state: { columnVisibility },
    onColumnVisibilityChange: setColumnVisibility,
    getCoreRowModel: getCoreRowModel(),
  })

  return (
    <div>
      <PageHeader title="Unlocked Episodes">
        <ColumnVisibilityButton table={table} />
      </PageHeader>
      <div className="px-[4%]">
        {!episodes ? (
          <DataTableSkeleton table={table} />
        ) : (
          <DataTable
            columns={tmdbMatchColumns}
            data={episodes}
            storageKey={STORAGE_KEY}
            columnVisibility={columnVisibility}
            onColumnVisibilityChange={setColumnVisibility}
          />
        )}
      </div>
    </div>
  )
}
