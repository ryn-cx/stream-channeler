// TODO: Validate
import { useQuery } from "@tanstack/react-query"
import type { VisibilityState } from "@tanstack/react-table"
import { getCoreRowModel, useReactTable } from "@tanstack/react-table"

import { ShowsService } from "@/client"
import { ColumnVisibilityButton } from "@/components/Common/ColumnVisibilityButton"
import { DataTable } from "@/components/Common/DataTable"
import { DataTableSkeleton } from "@/components/Common/DataTableSkeleton"
import { PageHeader } from "@/components/Common/PageHeader"
import { usePersistedJsonState } from "@/hooks/usePersistedState"
import { unvalidatedShowColumns } from "./unvalidatedShowColumns"
import { UNVALIDATED_SHOWS_QUERY_KEY } from "./unvalidatedShowsQuery"

const STORAGE_KEY = "admin-unvalidated-shows"

// TODO: Validate
export function UnvalidatedShowsAdminTable() {
  const [columnVisibility, setColumnVisibility] =
    usePersistedJsonState<VisibilityState>(`${STORAGE_KEY}-visibility`, {})

  const { data: shows } = useQuery({
    queryKey: UNVALIDATED_SHOWS_QUERY_KEY,
    queryFn: () => ShowsService.adminGetUnvalidatedShows({ limit: 1000 }),
  })

  const table = useReactTable({
    data: shows ?? [],
    columns: unvalidatedShowColumns,
    state: { columnVisibility },
    onColumnVisibilityChange: setColumnVisibility,
    getCoreRowModel: getCoreRowModel(),
  })

  return (
    <div>
      <PageHeader title="Unvalidated Shows">
        <ColumnVisibilityButton table={table} />
      </PageHeader>
      <div className="px-[4%]">
        {!shows ? (
          <DataTableSkeleton table={table} />
        ) : (
          <DataTable
            columns={unvalidatedShowColumns}
            data={shows}
            storageKey={STORAGE_KEY}
            columnVisibility={columnVisibility}
            onColumnVisibilityChange={setColumnVisibility}
          />
        )}
      </div>
    </div>
  )
}
