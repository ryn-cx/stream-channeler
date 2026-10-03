// TODO: Validate
import { useQuery } from "@tanstack/react-query"
import type { VisibilityState } from "@tanstack/react-table"
import { getCoreRowModel, useReactTable } from "@tanstack/react-table"
import { useState } from "react"

import {
  type IssueReportKind,
  type IssueReportMediaType,
  IssueReportsService,
} from "@/client"
import { ColumnVisibilityButton } from "@/components/Common/ColumnVisibilityButton"
import { DataTable } from "@/components/Common/DataTable"
import { DataTableSkeleton } from "@/components/Common/DataTableSkeleton"
import { PageHeader } from "@/components/Common/PageHeader"
import { Button } from "@/components/ui/button"
import { usePersistedJsonState } from "@/hooks/usePersistedState"
import {
  incorrectTitleReviewColumns,
  issueReportReviewColumns,
  kindLabel,
} from "./issueReportReviewColumns"

// TODO: Validate
function kindsFor(mediaType: IssueReportMediaType): IssueReportKind[] {
  if (mediaType === "title") {
    return ["incorrect_title", "unavailable", "other"]
  }
  return ["other"]
}

// TODO: Validate
export function IssueReportsReview() {
  const [mediaType, setMediaType] = useState<IssueReportMediaType>("title")
  const [kind, setKind] = useState<IssueReportKind | null>(null)
  const [showDeleted, setShowDeleted] = useState(false)
  const specialized = mediaType === "title" && kind === "incorrect_title"
  const storageKey = `admin-v2-issue-reports-${specialized ? "incorrect-title" : "all"}`
  const [columnVisibility, setColumnVisibility] =
    usePersistedJsonState<VisibilityState>(`${storageKey}-visibility`, {})

  const { data: reports } = useQuery({
    queryKey: ["issue-reports", "review", mediaType, kind, showDeleted],
    queryFn: () =>
      IssueReportsService.getIssueReports({
        mediaType,
        kind: kind ?? undefined,
        includeDeleted: showDeleted,
      }),
  })

  const columns = specialized
    ? incorrectTitleReviewColumns
    : issueReportReviewColumns

  const table = useReactTable({
    data: reports ?? [],
    columns,
    state: { columnVisibility },
    onColumnVisibilityChange: setColumnVisibility,
    getCoreRowModel: getCoreRowModel(),
  })

  return (
    <div>
      <PageHeader title="Issue Reports">
        <ColumnVisibilityButton table={table} />
      </PageHeader>
      <div className="flex flex-col gap-3 px-[4%] pb-4">
        <div className="flex flex-wrap gap-2">
          {(["title", "season", "episode"] as IssueReportMediaType[]).map(
            (value) => (
              <Button
                key={value}
                size="sm"
                variant={mediaType === value ? "default" : "outline"}
                onClick={() => {
                  setMediaType(value)
                  setKind(null)
                }}
              >
                {value === "title"
                  ? "Titles"
                  : value === "season"
                    ? "Seasons"
                    : "Episodes"}
              </Button>
            ),
          )}
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Button
            size="sm"
            variant={kind === null ? "secondary" : "ghost"}
            onClick={() => setKind(null)}
          >
            All Report Types
          </Button>
          {kindsFor(mediaType).map((value) => (
            <Button
              key={value}
              size="sm"
              variant={kind === value ? "secondary" : "ghost"}
              onClick={() => setKind(value)}
            >
              {kindLabel(value)}
            </Button>
          ))}
          <Button
            size="sm"
            variant={showDeleted ? "secondary" : "outline"}
            className="ml-auto"
            onClick={() => setShowDeleted(!showDeleted)}
          >
            {showDeleted ? "Hide Deleted" : "Show Deleted"}
          </Button>
        </div>
      </div>
      <div className="px-[4%]">
        {!reports ? (
          <DataTableSkeleton table={table} />
        ) : (
          <DataTable
            key={storageKey}
            columns={columns}
            data={reports}
            storageKey={storageKey}
            columnVisibility={columnVisibility}
            onColumnVisibilityChange={setColumnVisibility}
          />
        )}
      </div>
    </div>
  )
}
