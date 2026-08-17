// TODO: Validate
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { Flag, Pencil, Trash2 } from "lucide-react"
import { useState } from "react"
import type { IssueReportOutput } from "@/client"
import { IssueReportsService } from "@/client"
import { Button } from "@/components/ui/button"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import useAuth from "@/hooks/useAuth"
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"

export type IssueReportTarget = "episode" | "season" | "show"

/**
 * What each kind of record is usually reported for, and what it is called.
 *
 * The box is mostly filled in by whoever is watching rather than by whoever
 * imports, so the example is the thing that actually gets reported here: a show
 * is reported for being on a website nothing lists it under, and an episode for
 * being paired with the wrong one. Said in the words somebody watching would use
 * rather than in the ones the database uses.
 */
const TARGET_WORDING: Record<
  IssueReportTarget,
  { noun: string; placeholder: string }
> = {
  show: {
    noun: "show",
    placeholder: "This show is also on another website…",
  },
  season: {
    noun: "season",
    placeholder: "This season has the wrong episodes in it…",
  },
  episode: {
    noun: "episode",
    placeholder: "This is paired with the wrong episode…",
  },
}

interface IssueReportsSectionProps {
  target: IssueReportTarget
  mediaId: string
  reports: IssueReportOutput[]
  /** Query key of the information request the reports came back on. */
  informationQueryKey: unknown[]
}

// TODO: Validate
function createReport(
  target: IssueReportTarget,
  mediaId: string,
  report: string,
) {
  const requestBody = { report }
  if (target === "episode") {
    return IssueReportsService.createEpisodeIssueReport({
      episodeId: mediaId,
      requestBody,
    })
  }
  if (target === "season") {
    return IssueReportsService.createSeasonIssueReport({
      seasonId: mediaId,
      requestBody,
    })
  }
  return IssueReportsService.createShowIssueReport({
    showId: mediaId,
    requestBody,
  })
}

// TODO: Validate
function updateReport(
  target: IssueReportTarget,
  issueReportId: string,
  report: string,
) {
  const requestBody = { report }
  if (target === "episode") {
    return IssueReportsService.updateEpisodeIssueReport({
      issueReportId,
      requestBody,
    })
  }
  if (target === "season") {
    return IssueReportsService.updateSeasonIssueReport({
      issueReportId,
      requestBody,
    })
  }
  return IssueReportsService.updateShowIssueReport({
    issueReportId,
    requestBody,
  })
}

// TODO: Validate
function deleteReport(target: IssueReportTarget, issueReportId: string) {
  if (target === "episode") {
    return IssueReportsService.deleteEpisodeIssueReport({ issueReportId })
  }
  if (target === "season") {
    return IssueReportsService.deleteSeasonIssueReport({ issueReportId })
  }
  return IssueReportsService.deleteShowIssueReport({ issueReportId })
}

// TODO: Validate
/**
 * Every issue reported against one record, and the box for adding another.
 *
 * Anyone reading the media can report what is wrong with it, so the box is open
 * to visitors with no account. A report left without one has nobody to claim it,
 * so only a superuser can edit or delete it afterwards.
 */
export function IssueReportsSection({
  target,
  mediaId,
  reports,
  informationQueryKey,
}: IssueReportsSectionProps) {
  const [draft, setDraft] = useState("")
  const [editingId, setEditingId] = useState<string | null>(null)
  const [editDraft, setEditDraft] = useState("")
  const { user } = useAuth()
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const queryClient = useQueryClient()
  const wording = TARGET_WORDING[target]

  // TODO: Validate
  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: informationQueryKey })
    queryClient.invalidateQueries({ queryKey: ["issue-reports"] })
  }

  const createMutation = useMutation({
    mutationFn: () => createReport(target, mediaId, draft),
    onSuccess: () => {
      showSuccessToast("Issue reported")
      setDraft("")
      invalidate()
    },
    onError: (error: unknown) => handleError.call(showErrorToast, error as any),
  })

  const updateMutation = useMutation({
    mutationFn: () => updateReport(target, editingId!, editDraft),
    onSuccess: () => {
      showSuccessToast("Issue report updated")
      setEditingId(null)
      invalidate()
    },
    onError: (error: unknown) => handleError.call(showErrorToast, error as any),
  })

  const deleteMutation = useMutation({
    mutationFn: (issueReportId: string) => deleteReport(target, issueReportId),
    onSuccess: () => {
      showSuccessToast("Issue report deleted")
      invalidate()
    },
    onError: (error: unknown) => handleError.call(showErrorToast, error as any),
  })

  // TODO: Validate
  const canEdit = (report: IssueReportOutput) =>
    !!user && (user.is_superuser || user.id === report.user_id)

  return (
    <div className="mt-4 flex flex-col gap-3">
      <h3 className="font-medium">Reported Issues ({reports.length})</h3>

      {reports.length === 0 ? (
        <p className="text-sm text-muted-foreground">
          Nothing has been reported against this {wording.noun} yet.
        </p>
      ) : (
        <ul className="flex flex-col gap-2">
          {reports.map((report) => (
            <li key={report.id} className="rounded border p-3">
              <div className="flex items-start justify-between gap-2">
                <p className="text-xs text-muted-foreground">
                  {report.username ?? "Anonymous"} ·{" "}
                  {new Date(report.created_at).toLocaleString()}
                </p>
                {canEdit(report) && (
                  <div className="flex shrink-0 gap-1">
                    <Button
                      variant="ghost"
                      size="icon-sm"
                      onClick={() => {
                        setEditingId(report.id)
                        setEditDraft(report.report)
                      }}
                    >
                      <Pencil />
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon-sm"
                      disabled={deleteMutation.isPending}
                      onClick={() => deleteMutation.mutate(report.id)}
                    >
                      <Trash2 />
                    </Button>
                  </div>
                )}
              </div>
              {editingId === report.id ? (
                <div className="mt-2 flex flex-col gap-2">
                  <Textarea
                    rows={3}
                    value={editDraft}
                    onChange={(event) => setEditDraft(event.target.value)}
                  />
                  <div className="flex gap-2">
                    <Button
                      size="sm"
                      disabled={
                        editDraft.trim().length === 0 ||
                        updateMutation.isPending
                      }
                      onClick={() => updateMutation.mutate()}
                    >
                      Save
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => setEditingId(null)}
                    >
                      Cancel
                    </Button>
                  </div>
                </div>
              ) : (
                <p className="mt-1 whitespace-pre-wrap text-sm">
                  {report.report}
                </p>
              )}
            </li>
          ))}
        </ul>
      )}

      <div className="flex flex-col gap-2">
        <Label htmlFor={`issue-report-${mediaId}`}>Report an issue</Label>
        <Textarea
          id={`issue-report-${mediaId}`}
          rows={3}
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          placeholder={wording.placeholder}
        />
        <Button
          className="self-start"
          disabled={draft.trim().length === 0 || createMutation.isPending}
          onClick={() => createMutation.mutate()}
        >
          <Flag />
          Report Issue
        </Button>
      </div>
    </div>
  )
}
