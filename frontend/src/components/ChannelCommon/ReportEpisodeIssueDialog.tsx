// TODO: Validate
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { useState } from "react"
import { EpisodesService } from "@/client"
import { ModalContent } from "@/components/Common/ModalContent"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogBody,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"

interface ReportEpisodeIssueDialogProps {
  episodeId: string
  episodeName: string | null
  currentReport: string | null
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function ReportEpisodeIssueDialog({
  episodeId,
  episodeName,
  currentReport,
  open,
  onOpenChange,
}: ReportEpisodeIssueDialogProps) {
  const [report, setReport] = useState(currentReport ?? "")
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const queryClient = useQueryClient()

  const invalidate = () => {
    queryClient.invalidateQueries({
      queryKey: ["episode-information", episodeId],
    })
    queryClient.invalidateQueries({ queryKey: ["episodes"] })
  }

  const reportMutation = useMutation({
    mutationFn: () =>
      EpisodesService.reportEpisodeIssue({
        episodeId,
        requestBody: { report },
      }),
    onSuccess: () => {
      showSuccessToast("Issue reported")
      invalidate()
      onOpenChange(false)
    },
    onError: (error: unknown) => handleError.call(showErrorToast, error as any),
  })

  const clearMutation = useMutation({
    mutationFn: () => EpisodesService.clearEpisodeIssueReport({ episodeId }),
    onSuccess: () => {
      showSuccessToast("Issue report cleared")
      invalidate()
      onOpenChange(false)
    },
    onError: (error: unknown) => handleError.call(showErrorToast, error as any),
  })

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <ModalContent>
        <DialogHeader>
          <DialogTitle>Report Issue</DialogTitle>
          <DialogDescription>
            Say what is wrong with "{episodeName ?? ""}" — a wrong TMDB match,
            wrong numbering, a bad link, or anything else. The report stays on
            the episode through imports.
          </DialogDescription>
        </DialogHeader>

        <DialogBody className="flex flex-col gap-2">
          <Label htmlFor="episode-issue-report">Issue</Label>
          <Textarea
            id="episode-issue-report"
            rows={5}
            value={report}
            onChange={(event) => setReport(event.target.value)}
            placeholder="Matched to the wrong TMDB episode…"
          />
        </DialogBody>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          {currentReport ? (
            <Button
              variant="destructive"
              onClick={() => clearMutation.mutate()}
              disabled={clearMutation.isPending}
            >
              Clear Report
            </Button>
          ) : null}
          <Button
            onClick={() => reportMutation.mutate()}
            disabled={report.trim().length === 0 || reportMutation.isPending}
          >
            Report Issue
          </Button>
        </DialogFooter>
      </ModalContent>
    </Dialog>
  )
}
