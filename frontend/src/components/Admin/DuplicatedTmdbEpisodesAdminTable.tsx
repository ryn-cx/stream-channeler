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
import { duplicatedTmdbEpisodeColumns } from "./duplicatedTmdbEpisodeColumns"
import { DUPLICATED_TMDB_EPISODES_QUERY_KEY } from "./duplicatedTmdbEpisodesQuery"

const STORAGE_KEY = "admin-duplicated-tmdb-episodes"

// TODO: Validate
export function DuplicatedTmdbEpisodesAdminTable() {
  const [columnVisibility, setColumnVisibility] =
    usePersistedJsonState<VisibilityState>(`${STORAGE_KEY}-visibility`, {})

  const { data: links } = useQuery({
    queryKey: DUPLICATED_TMDB_EPISODES_QUERY_KEY,
    queryFn: () =>
      EpisodesService.adminGetDuplicatedTmdbEpisodes({ limit: 1000 }),
  })

  const table = useReactTable({
    data: links ?? [],
    columns: duplicatedTmdbEpisodeColumns,
    state: { columnVisibility },
    onColumnVisibilityChange: setColumnVisibility,
    getCoreRowModel: getCoreRowModel(),
  })

  return (
    <div>
      <PageHeader title="Duplicated TMDB Episodes">
        <ColumnVisibilityButton table={table} />
      </PageHeader>
      <div className="px-[4%]">
        {!links ? (
          <DataTableSkeleton table={table} />
        ) : (
          <DataTable
            columns={duplicatedTmdbEpisodeColumns}
            data={links}
            storageKey={STORAGE_KEY}
            columnVisibility={columnVisibility}
            onColumnVisibilityChange={setColumnVisibility}
          />
        )}
      </div>
    </div>
  )
}
