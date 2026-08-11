// TODO: Validate
import type { ColumnDef } from "@tanstack/react-table"

import type { IssueReportListOutput, IssueReportMediaType } from "@/client"
import { DateCell } from "@/components/Common/TableCells"

/** One record, with every issue reported against it gathered into one row. */
export interface GroupedIssueReport {
  id: string
  media_type: IssueReportMediaType
  media_name: string | null
  season_name: string | null
  show_name: string | null
  source_name: string | null
  report_count: number
  /** Every report on the record, run together into the one cell. */
  reports: string
  /** When the newest report on the record was left. */
  latest_report_at: string
}

// TODO: Validate
export function groupIssueReports(
  reports: IssueReportListOutput[],
): GroupedIssueReport[] {
  const grouped = new Map<string, GroupedIssueReport>()
  for (const report of reports) {
    const existing = grouped.get(report.media_id)
    if (existing) {
      existing.report_count += 1
      existing.reports = `${existing.reports}\n\n${report.report}`
      continue
    }
    grouped.set(report.media_id, {
      id: report.media_id,
      media_type: report.media_type,
      media_name: report.media_name,
      season_name: report.season_name,
      show_name: report.show_name,
      source_name: report.source_name,
      report_count: 1,
      reports: report.report,
      latest_report_at: report.created_at,
    })
  }
  // The reports arrive newest first, so the first one seen for a record is the
  // newest, and the rest are run on in that order.
  return [...grouped.values()]
}

export const issueReportColumns: ColumnDef<IssueReportListOutput>[] = [
  {
    id: "media_type",
    accessorFn: (row) => row.media_type,
    header: "Type",
    meta: { filterVariant: "select" },
    filterFn: "equalsString",
  },
  {
    id: "media_name",
    accessorFn: (row) => row.media_name ?? "Unnamed",
    header: "Record",
    cell: ({ row }) => (
      <span className="font-medium">
        {row.original.media_name ?? "Unnamed"}
      </span>
    ),
  },
  {
    id: "show_name",
    accessorFn: (row) => row.show_name ?? "",
    header: "Show",
  },
  {
    id: "season_name",
    accessorFn: (row) => row.season_name ?? "",
    header: "Season",
  },
  {
    id: "source_name",
    accessorFn: (row) => row.source_name ?? "Unknown source",
    header: "Source",
    meta: { filterVariant: "select" },
    filterFn: "equalsString",
  },
  {
    id: "username",
    accessorFn: (row) => row.username ?? "Anonymous",
    header: "Reported by",
    meta: { filterVariant: "select" },
    filterFn: "equalsString",
  },
  {
    accessorKey: "report",
    header: "Issue",
    cell: ({ row }) => (
      <span className="block max-w-md whitespace-pre-wrap">
        {row.original.report}
      </span>
    ),
  },
  {
    accessorKey: "created_at",
    header: "Reported",
    meta: { filterVariant: "dateRange" },
    cell: ({ row }) => <DateCell value={row.original.created_at} />,
  },
]

export const groupedIssueReportColumns: ColumnDef<GroupedIssueReport>[] = [
  {
    id: "media_name",
    accessorFn: (row) => row.media_name ?? "Unnamed",
    header: "Record",
    cell: ({ row }) => (
      <span className="font-medium">
        {row.original.media_name ?? "Unnamed"}
      </span>
    ),
  },
  {
    id: "show_name",
    accessorFn: (row) => row.show_name ?? "",
    header: "Show",
  },
  {
    id: "season_name",
    accessorFn: (row) => row.season_name ?? "",
    header: "Season",
  },
  {
    id: "source_name",
    accessorFn: (row) => row.source_name ?? "Unknown source",
    header: "Source",
    meta: { filterVariant: "select" },
    filterFn: "equalsString",
  },
  {
    accessorKey: "report_count",
    header: "Reports",
    meta: { filterVariant: "range" },
    cell: ({ row }) => (
      <span className="tabular-nums">{row.original.report_count}</span>
    ),
  },
  {
    accessorKey: "reports",
    header: "Issues",
    cell: ({ row }) => (
      <span className="block max-w-xl whitespace-pre-wrap">
        {row.original.reports}
      </span>
    ),
  },
  {
    accessorKey: "latest_report_at",
    header: "Latest",
    meta: { filterVariant: "dateRange" },
    cell: ({ row }) => <DateCell value={row.original.latest_report_at} />,
  },
]
