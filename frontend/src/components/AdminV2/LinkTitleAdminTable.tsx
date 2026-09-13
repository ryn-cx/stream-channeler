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
import { linkTitleColumns } from "./linkTitleColumns"
import { TITLES_MISSING_SOURCES_QUERY_KEY } from "./titlesMissingSourcesQuery"

const STORAGE_KEY = "admin-v2-link-title"

// TODO: Validate
export function LinkTitleAdminTable() {
  const [columnVisibility, setColumnVisibility] =
    usePersistedJsonState<VisibilityState>(`${STORAGE_KEY}-visibility`, {})

  const { data: titles } = useQuery({
    queryKey: TITLES_MISSING_SOURCES_QUERY_KEY,
    queryFn: () => TitlesService.adminGetTitlesMissingSources({ limit: 1000 }),
  })

  const table = useReactTable({
    data: titles ?? [],
    columns: linkTitleColumns,
    state: { columnVisibility },
    onColumnVisibilityChange: setColumnVisibility,
    getCoreRowModel: getCoreRowModel(),
  })

  return (
    <div>
      <PageHeader title="Link Title">
        <ColumnVisibilityButton table={table} />
      </PageHeader>
      <div className="px-[4%]">
        {!titles ? (
          <DataTableSkeleton table={table} />
        ) : (
          <DataTable
            columns={linkTitleColumns}
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
