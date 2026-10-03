// TODO: Validate
import { useMutation, useQueryClient } from "@tanstack/react-query"
import type { ColumnDef } from "@tanstack/react-table"

import {
  type IssueReportKind,
  type IssueReportListOutput,
  type IssueReportResolution,
  IssueReportsService,
} from "@/client"
import { DateCell } from "@/components/Common/TableCells"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import useCustomToast from "@/hooks/useCustomToast"
import { useOpenMedia } from "@/hooks/useOpenMedia"
import { handleError } from "@/utils"

// TODO: Validate
export function kindLabel(kind: IssueReportKind) {
  switch (kind) {
    case "incorrect_title":
      return "Incorrect Title Information"
    case "unavailable":
      return "No Longer Available"
    case "other":
      return "Other"
  }
}

// TODO: Validate
function MediaCell({ report }: { report: IssueReportListOutput }) {
  const openMedia = useOpenMedia()
  // TODO: Validate
  const open = () => {
    if (report.media_type === "title") {
      openMedia({ kind: "title", titleId: report.media_id })
    } else if (report.media_type === "season") {
      openMedia({ kind: "season", seasonIds: [report.media_id] })
    } else {
      openMedia({ kind: "episode", episode: { id: report.media_id } })
    }
  }
  return (
    <button
      type="button"
      onClick={open}
      className="text-left font-medium whitespace-normal wrap-break-word hover:underline"
    >
      {report.media_name ?? "Unnamed"}
      <span className="block text-xs font-normal text-muted-foreground">
        {[report.source_key, report.title_name, report.season_name]
          .filter(Boolean)
          .join(" · ")}
      </span>
    </button>
  )
}

// TODO: Validate
function ResolveButtons({ report }: { report: IssueReportListOutput }) {
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const queryClient = useQueryClient()
  const mutation = useMutation({
    mutationFn: (resolution: IssueReportResolution) =>
      IssueReportsService.resolveTitleReport({
        issueReportId: report.id,
        requestBody: { resolution },
      }),
    onSuccess: () => {
      showSuccessToast("Report resolved")
      queryClient.invalidateQueries({ queryKey: ["issue-reports"] })
      queryClient.invalidateQueries({ queryKey: ["titles"] })
      queryClient.invalidateQueries({
        queryKey: ["title-information", report.media_id],
      })
      queryClient.invalidateQueries({ queryKey: ["tmdb-title"] })
    },
    onError: (error: unknown) =>
      handleError.call(
        showErrorToast,
        error as Parameters<typeof handleError>[0],
      ),
  })

  if (report.deleted_at) {
    return <Badge variant="outline">Resolved</Badge>
  }
  const canLink = Boolean(report.suggestion) && !mutation.isPending
  return (
    <div className="flex flex-wrap gap-2">
      <Button
        size="sm"
        disabled={!canLink}
        onClick={() => mutation.mutate("add_link")}
      >
        Add Link
      </Button>
      <Button
        size="sm"
        variant="secondary"
        disabled={!canLink}
        onClick={() => mutation.mutate("replace_links")}
      >
        Replace Links
      </Button>
      <Button
        size="sm"
        variant="outline"
        disabled={mutation.isPending}
        onClick={() => mutation.mutate("ignore")}
      >
        Ignore
      </Button>
    </div>
  )
}

// TODO: Validate
export const issueReportReviewColumns: ColumnDef<IssueReportListOutput>[] = [
  {
    id: "created_at",
    accessorFn: (row) => row.created_at,
    header: "When",
    meta: { filterVariant: "dateRange", cellClassName: "align-top" },
    cell: ({ row }) => <DateCell value={row.original.created_at} />,
  },
  {
    id: "media_name",
    accessorFn: (row) => row.media_name ?? "",
    header: "Reported",
    meta: { cellClassName: "align-top" },
    cell: ({ row }) => <MediaCell report={row.original} />,
  },
  {
    id: "kind",
    accessorFn: (row) => kindLabel(row.kind),
    header: "Report Type",
    meta: { filterVariant: "select", cellClassName: "align-top" },
    filterFn: "equalsString",
    cell: ({ row }) => (
      <Badge variant="outline">{kindLabel(row.original.kind)}</Badge>
    ),
  },
  {
    id: "report",
    accessorFn: (row) => row.report,
    header: "Report",
    meta: { cellClassName: "align-top" },
    cell: ({ row }) => (
      <span className="whitespace-pre-wrap wrap-break-word text-sm">
        {row.original.report}
      </span>
    ),
  },
  {
    id: "username",
    accessorFn: (row) => row.username ?? "Anonymous",
    header: "Reported By",
    meta: { cellClassName: "align-top" },
  },
  {
    id: "deleted_at",
    accessorFn: (row) => (row.deleted_at ? "Deleted" : "Open"),
    header: "Status",
    meta: { filterVariant: "select", cellClassName: "align-top" },
    filterFn: "equalsString",
    cell: ({ row }) =>
      row.original.deleted_at ? (
        <Badge variant="outline">Deleted</Badge>
      ) : (
        <Badge variant="secondary">Open</Badge>
      ),
  },
]

// TODO: Validate
export const incorrectTitleReviewColumns: ColumnDef<IssueReportListOutput>[] = [
  {
    id: "created_at",
    accessorFn: (row) => row.created_at,
    header: "When",
    meta: { filterVariant: "dateRange", cellClassName: "align-top" },
    cell: ({ row }) => <DateCell value={row.original.created_at} />,
  },
  {
    id: "media_name",
    accessorFn: (row) => row.media_name ?? "",
    header: "Source Title",
    meta: { cellClassName: "align-top" },
    cell: ({ row }) => <MediaCell report={row.original} />,
  },
  {
    id: "current_links",
    accessorFn: (row) =>
      (row.current_links ?? []).map((link) => link.name ?? "").join(", "),
    header: "Current Links",
    meta: { cellClassName: "align-top" },
    cell: ({ row }) => {
      const links = row.original.current_links ?? []
      if (links.length === 0) {
        return <span className="text-muted-foreground">Not linked</span>
      }
      return (
        <ul className="space-y-1 text-sm">
          {links.map((link) => (
            <li key={link.id}>
              {link.url ? (
                <a
                  href={link.url}
                  target="_blank"
                  rel="noreferrer"
                  className="hover:underline"
                >
                  {link.name ?? "Unnamed"}
                  {link.year ? ` (${link.year})` : ""}
                </a>
              ) : (
                <span>
                  {link.name ?? "Unnamed"}
                  {link.year ? ` (${link.year})` : ""}
                </span>
              )}
            </li>
          ))}
        </ul>
      )
    },
  },
  {
    id: "suggestion",
    accessorFn: (row) => row.suggestion?.name ?? "",
    header: "User Suggested",
    meta: { cellClassName: "align-top" },
    cell: ({ row }) => {
      const suggestion = row.original.suggestion
      if (!suggestion) {
        return (
          <span className="text-muted-foreground">
            The correct title is not listed
          </span>
        )
      }
      return (
        <a
          href={suggestion.url}
          target="_blank"
          rel="noreferrer"
          className="text-sm hover:underline"
        >
          {suggestion.name}
          {suggestion.year ? ` (${suggestion.year})` : ""}
        </a>
      )
    },
  },
  {
    id: "username",
    accessorFn: (row) => row.username ?? "Anonymous",
    header: "Reported By",
    meta: { cellClassName: "align-top" },
  },
  {
    id: "actions",
    header: "Actions",
    meta: { cellClassName: "align-top" },
    enableSorting: false,
    enableColumnFilter: false,
    cell: ({ row }) => <ResolveButtons report={row.original} />,
  },
]
