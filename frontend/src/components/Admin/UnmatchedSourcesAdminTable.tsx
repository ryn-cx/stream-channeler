// TODO: Validate
import { useQuery } from "@tanstack/react-query"
import type { VisibilityState } from "@tanstack/react-table"
import { getCoreRowModel, useReactTable } from "@tanstack/react-table"

import { UnmatchedSourcesService } from "@/client"
import { ColumnVisibilityButton } from "@/components/Common/ColumnVisibilityButton"
import { DataTable } from "@/components/Common/DataTable"
import { DataTableSkeleton } from "@/components/Common/DataTableSkeleton"
import { PageHeader } from "@/components/Common/PageHeader"
import { usePersistedJsonState } from "@/hooks/usePersistedState"
import { unmatchedSourceColumns } from "./unmatchedSourceColumns"
import { UNMATCHED_SOURCES_QUERY_KEY } from "./unmatchedSourcesQuery"

const storageKey = "admin-unmatched-sources"

// TODO: Validate
export function UnmatchedSourcesAdminTable({ title }: { title: string }) {
  const [columnVisibility, setColumnVisibility] =
    usePersistedJsonState<VisibilityState>(`${storageKey}-visibility`, {})

  const { data: unmatchedSources } = useQuery({
    queryKey: UNMATCHED_SOURCES_QUERY_KEY,
    queryFn: () => UnmatchedSourcesService.adminGetUnmatchedSources(),
  })

  const table = useReactTable({
    data: unmatchedSources ?? [],
    columns: unmatchedSourceColumns,
    state: { columnVisibility },
    onColumnVisibilityChange: setColumnVisibility,
    getCoreRowModel: getCoreRowModel(),
  })

  return (
    <div>
      <PageHeader title={title}>
        <ColumnVisibilityButton table={table} />
      </PageHeader>
      <div className="px-[4%]">
        {!unmatchedSources ? (
          <DataTableSkeleton table={table} />
        ) : (
          <DataTable
            columns={unmatchedSourceColumns}
            data={unmatchedSources}
            storageKey={storageKey}
            columnVisibility={columnVisibility}
            onColumnVisibilityChange={setColumnVisibility}
          />
        )}
      </div>
    </div>
  )
}
