// TODO: Validate
import { useMutation, useQuery } from "@tanstack/react-query"
import { ChevronDown, ThumbsDown, ThumbsUp } from "lucide-react"
import type { ReactNode } from "react"
import { useEffect, useRef, useState } from "react"

import type { PluginSearchResult } from "@/client"
import { IssueReportsService } from "@/client"
import { TitleInformationSummary } from "@/components/ChannelCommon/TitleInformationDialog"
import { TitleMatches } from "@/components/ChannelCommon/TitleMatches"
import { Button } from "@/components/ui/button"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import useCustomToast from "@/hooks/useCustomToast"
import { cn } from "@/lib/utils"
import { handleError } from "@/utils"

// TODO: Validate
function scrollableAncestor(element: HTMLElement) {
  let parent = element.parentElement
  while (parent) {
    const overflow = getComputedStyle(parent).overflowY
    if (overflow === "auto" || overflow === "scroll") {
      return parent
    }
    parent = parent.parentElement
  }
  return null
}

export type Problem = "wrong-title" | "unavailable" | "other"

export interface ReportIssueSource {
  titleId: string
  label: string
}

// TODO: Validate
function ExistingReports({ titleId }: { titleId: string }) {
  const [votes, setVotes] = useState<Record<string, "up" | "down">>({})

  const { data: reports } = useQuery({
    queryKey: ["title-issue-reports", titleId],
    queryFn: () => IssueReportsService.getTitleIssueReports({ titleId }),
    enabled: Boolean(titleId),
  })

  if (!reports?.length) return null

  // TODO: Validate
  const vote = (reportId: string, direction: "up" | "down") =>
    setVotes((current) => {
      const { [reportId]: previous, ...rest } = current
      return previous === direction ? rest : { ...rest, [reportId]: direction }
    })

  return (
    <div className="space-y-2">
      <Label>Already reported</Label>
      {reports.map((report) => (
        <div
          key={report.id}
          className="flex items-start gap-2 rounded-md border px-3 py-2"
        >
          <div className="min-w-0 flex-1">
            <p className="text-sm">{report.report}</p>
            <p className="text-xs text-muted-foreground">
              {report.username ?? "Anonymous"} ·{" "}
              {new Date(report.created_at).toLocaleDateString()}
            </p>
          </div>
          <Button
            type="button"
            variant="ghost"
            size="icon"
            onClick={() => vote(report.id, "up")}
            className={cn(votes[report.id] === "up" && "text-emerald-500")}
          >
            <ThumbsUp className="size-4" />
          </Button>
          <Button
            type="button"
            variant="ghost"
            size="icon"
            onClick={() => vote(report.id, "down")}
            className={cn(votes[report.id] === "down" && "text-red-500")}
          >
            <ThumbsDown className="size-4" />
          </Button>
        </div>
      ))}
    </div>
  )
}

interface ReportIssueFormProps {
  sources: ReportIssueSource[]
  actions?: ReactNode
  onSent?: () => void
  fixedProblem?: Problem
}

// TODO: Validate
export function ReportIssueForm({
  sources,
  actions,
  onSent,
  fixedProblem,
}: ReportIssueFormProps) {
  const { showSuccessToast, showErrorToast } = useCustomToast()
  // A form given one source is read inside something already about that source,
  // which has the title at the top of it and nothing to pick between.
  const fixedSource = sources.length === 1 ? sources[0] : null
  const [titleId, setTitleId] = useState(fixedSource?.titleId ?? "")
  const [problem, setProblem] = useState<Problem | null>(fixedProblem ?? null)
  const [picked, setPicked] = useState<PluginSearchResult | null>(null)
  const [notListed, setNotListed] = useState(false)
  const [details, setDetails] = useState("")
  const rootRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const root = rootRef.current
    if (!titleId || fixedSource || !root) {
      return
    }
    const scroller = scrollableAncestor(root)
    if (!scroller) {
      return
    }
    const observer = new ResizeObserver(() => {
      scroller.scrollTop = scroller.scrollHeight
    })
    observer.observe(root)
    const stop = window.setTimeout(() => observer.disconnect(), 500)
    return () => {
      observer.disconnect()
      window.clearTimeout(stop)
    }
  }, [titleId, fixedSource])

  const mutation = useMutation({
    mutationFn: (report: string) =>
      IssueReportsService.createTitleIssueReport({
        titleId,
        requestBody: {
          report,
          anonymous: false,
          kind: {
            "wrong-title": "incorrect_title" as const,
            unavailable: "unavailable" as const,
            other: "other" as const,
          }[problem ?? "other"],
        },
      }),
    onSuccess: () => {
      showSuccessToast("Thanks, the report was sent.")
      setPicked(null)
      setNotListed(false)
      setDetails("")
      setProblem(fixedProblem ?? null)
      onSent?.()
    },
    onError: (error: unknown) => handleError.call(showErrorToast, error as any),
  })

  // TODO: Validate
  const reportText = () => {
    if (!problem) return ""
    if (problem === "unavailable") return "Title is no longer available."
    if (problem === "other") return details.trim()
    if (notListed) {
      return "Incorrect Title Information. The correct title is not listed."
    }
    const correct = picked
      ? ` The correct title is ${picked.title}${
          picked.year ? ` (${picked.year})` : ""
        }${picked.media_identifier ? ` [${picked.media_identifier}]` : ""}.`
      : ""
    return `Incorrect Title Information.${correct}`
  }

  const report = reportText()

  return (
    <div ref={rootRef} className="space-y-4">
      <div className="space-y-2">
        {!fixedSource && <Label>Which source is the problem?</Label>}
        {!fixedSource &&
          sources.map((source) => (
            <button
              key={source.titleId}
              type="button"
              onClick={() => {
                setTitleId(source.titleId)
                setPicked(null)
                setNotListed(false)
              }}
              className={cn(
                "flex w-full items-center justify-between rounded-md border px-3 py-2 text-left text-sm hover:bg-muted",
                titleId === source.titleId && "border-primary bg-muted",
              )}
            >
              {source.label}
            </button>
          ))}
        {titleId && !fixedSource && (
          <TitleInformationSummary titleId={titleId} />
        )}
        {titleId && <ExistingReports titleId={titleId} />}
      </div>

      {titleId && (
        <div className="space-y-2">
          {fixedProblem ? null : <Label>What is wrong?</Label>}
          {(
            [
              ["wrong-title", "Incorrect Title Information"],
              ["unavailable", "Title is no longer available"],
              ["other", "Something else"],
            ] as [Problem, string][]
          )
            .filter(([value]) => !fixedProblem || value === fixedProblem)
            .map(([value, label]) => (
              <div key={value} className="space-y-2">
                {fixedProblem ? null : (
                  <button
                    type="button"
                    onClick={() => setProblem(problem === value ? null : value)}
                    className={cn(
                      "flex w-full items-center justify-between rounded-md border px-3 py-2 text-left text-sm hover:bg-muted",
                      problem === value && "border-primary bg-muted",
                    )}
                  >
                    {label}
                    {value !== "unavailable" && (
                      <ChevronDown
                        className={cn(
                          "size-4 transition-transform",
                          problem === value && "rotate-180",
                        )}
                      />
                    )}
                  </button>
                )}

                {problem === "wrong-title" && value === "wrong-title" && (
                  <TitleMatches
                    titleId={titleId}
                    picked={picked}
                    notListed={notListed}
                    onPick={(result) => {
                      setNotListed(false)
                      setPicked(result)
                    }}
                    onNotListed={() => {
                      setPicked(null)
                      setNotListed(!notListed)
                    }}
                  />
                )}

                {problem === "other" && value === "other" && (
                  <div className="space-y-2">
                    <Label htmlFor="report-details">What is the problem?</Label>
                    <Textarea
                      id="report-details"
                      value={details}
                      onChange={(event) => setDetails(event.target.value)}
                      placeholder="Describe what is wrong…"
                    />
                  </div>
                )}
              </div>
            ))}
        </div>
      )}

      <div className="flex justify-end gap-2">
        {actions}
        {titleId && (
          <Button
            variant="destructive"
            onClick={() => mutation.mutate(report)}
            disabled={!report || mutation.isPending}
          >
            Send report
          </Button>
        )}
      </div>
    </div>
  )
}
