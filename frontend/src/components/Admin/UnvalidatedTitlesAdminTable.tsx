// TODO: Validate
import { useQuery } from "@tanstack/react-query"
import type { VisibilityState } from "@tanstack/react-table"
import { getCoreRowModel, useReactTable } from "@tanstack/react-table"

import { TitlesService } from "@/client"
import { ColumnVisibilityButton } from "@/components/Common/ColumnVisibilityButton"
import { DataTable } from "@/components/Common/DataTable"
import { DataTableSkeleton } from "@/components/Common/DataTableSkeleton"
import { PageHeader } from "@/components/Common/PageHeader"
import { usePersistedJsonState } from "@/hooks/usePersistedState"
import { unvalidatedTitleColumns } from "./unvalidatedTitleColumns"
import { UNVALIDATED_TITLES_QUERY_KEY } from "./unvalidatedTitlesQuery"

const STORAGE_KEY = "admin-unvalidated-titles"

// TODO: Validate
export function UnvalidatedTitlesAdminTable() {
  const [columnVisibility, setColumnVisibility] =
    usePersistedJsonState<VisibilityState>(`${STORAGE_KEY}-visibility`, {})

  const { data: titles } = useQuery({
    queryKey: UNVALIDATED_TITLES_QUERY_KEY,
    queryFn: () => TitlesService.adminGetUnvalidatedTitles({ limit: 1000 }),
  })

  const table = useReactTable({
    data: titles ?? [],
    columns: unvalidatedTitleColumns,
    state: { columnVisibility },
    onColumnVisibilityChange: setColumnVisibility,
    getCoreRowModel: getCoreRowModel(),
  })

  return (
    <div>
      <PageHeader title="Unvalidated Titles">
        <ColumnVisibilityButton table={table} />
      </PageHeader>
      <div className="px-[4%]">
        {!titles ? (
          <DataTableSkeleton table={table} />
        ) : (
          <DataTable
            columns={unvalidatedTitleColumns}
            data={titles}
            storageKey={STORAGE_KEY}
            columnVisibility={columnVisibility}
            onColumnVisibilityChange={setColumnVisibility}
          />
        )}
      </div>
    </div>
  )
}
