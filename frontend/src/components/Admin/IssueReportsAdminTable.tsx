// TODO: Validate
import { useQuery } from "@tanstack/react-query"
import type { VisibilityState } from "@tanstack/react-table"
import { getCoreRowModel, useReactTable } from "@tanstack/react-table"

import type { IssueReportMediaType } from "@/client"
import { IssueReportsService } from "@/client"
import { ColumnVisibilityButton } from "@/components/Common/ColumnVisibilityButton"
import { DataTable } from "@/components/Common/DataTable"
import { DataTableSkeleton } from "@/components/Common/DataTableSkeleton"
import { PageHeader } from "@/components/Common/PageHeader"
import { usePersistedJsonState } from "@/hooks/usePersistedState"
import {
  groupedIssueReportColumns,
  groupIssueReports,
  issueReportColumns,
} from "./issueReportColumns"

interface IssueReportsAdminTableProps {
  title: string
  /** Left unset to read the reports on every kind of record. */
  mediaType?: IssueReportMediaType
  /**
   * Whether the reports on one record are gathered into a single row, with a
   * count and every report run together into the one cell.
   */
  grouped?: boolean
}

export function IssueReportsAdminTable({
  title,
  mediaType,
  grouped = false,
}: IssueReportsAdminTableProps) {
  const storageKey = `admin-issue-reports-${mediaType ?? "all"}${grouped ? "-grouped" : ""}`
  const [columnVisibility, setColumnVisibility] =
    usePersistedJsonState<VisibilityState>(`${storageKey}-visibility`, {})

  const { data: reports } = useQuery({
    queryKey: ["issue-reports", mediaType ?? "all"],
    queryFn: () => IssueReportsService.getIssueReports({ mediaType }),
  })

  const groupedReports = reports ? groupIssueReports(reports) : undefined
  const columns = grouped ? groupedIssueReportColumns : issueReportColumns
  const rows = grouped ? groupedReports : reports

  const table = useReactTable({
    data: (rows ?? []) as any[],
    columns: columns as any[],
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
        {!rows ? (
          <DataTableSkeleton table={table} />
        ) : (
          <DataTable
            columns={columns as any[]}
            data={rows as any[]}
            storageKey={storageKey}
            columnVisibility={columnVisibility}
            onColumnVisibilityChange={setColumnVisibility}
          />
        )}
      </div>
    </div>
  )
}
