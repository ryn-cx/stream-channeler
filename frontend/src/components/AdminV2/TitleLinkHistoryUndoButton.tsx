// TODO: Validate
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { Eye, RotateCcw, Unlink } from "lucide-react"

import type { TitleLinkHistoryOutput } from "@/client"
import { TitlesService, UnmatchedTitlesService } from "@/client"
import { Button } from "@/components/ui/button"
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"
import { TITLE_LINK_HISTORY_QUERY_KEY } from "./titleLinkHistoryQuery"
import { UNMATCHED_TITLES_QUERY_KEY } from "./unmatchedTitlesQuery"

// TODO: Validate
export function TitleLinkHistoryUndoButton({
  entry,
}: {
  entry: TitleLinkHistoryOutput
}) {
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const queryClient = useQueryClient()
  const ignored = entry.kind === "ignored"
  const absent = entry.kind === "absent"

  const undoMutation = useMutation({
    mutationFn: async () => {
      if (absent) {
        await TitlesService.adminUnmarkTitleAbsentFromTmdb({
          titleId: entry.title_id,
        })
        return
      }
      if (ignored) {
        await UnmatchedTitlesService.adminUnignoreUnmatchedTitle({
          unmatchedTitleId: entry.unmatched_title_id ?? entry.id,
        })
        return
      }
      await TitlesService.adminUnlinkTitleFromTmdb({
        titleId: entry.title_id,
        tmdbTitleId: entry.tmdb_title_id ?? "",
      })
    },
    onSuccess: () => {
      if (absent) {
        showSuccessToast("Title no longer marked as absent from TMDB")
        return
      }
      showSuccessToast(ignored ? "Title no longer ignored" : "Title unlinked")
    },
    onError: (error: unknown) =>
      handleError.call(
        showErrorToast,
        error as Parameters<typeof handleError>[0],
      ),
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: TITLE_LINK_HISTORY_QUERY_KEY })
      queryClient.invalidateQueries({ queryKey: ["titles"] })
      queryClient.invalidateQueries({ queryKey: UNMATCHED_TITLES_QUERY_KEY })
    },
  })

  return (
    <Button
      type="button"
      variant={ignored || absent ? "outline" : "destructive"}
      size="sm"
      disabled={undoMutation.isPending}
      onClick={() => undoMutation.mutate()}
    >
      {absent ? <RotateCcw /> : ignored ? <Eye /> : <Unlink />}
      {absent ? "Unmark" : ignored ? "Stop ignoring" : "Unlink"}
    </Button>
  )
}
