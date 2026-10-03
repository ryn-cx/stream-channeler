// TODO: Validate
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { Eye, RotateCcw, Unlink } from "lucide-react"

import type { EpisodeLinkHistoryOutput } from "@/client"
import { EpisodesService } from "@/client"
import { Button } from "@/components/ui/button"
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"
import { EPISODE_LINK_HISTORY_QUERY_KEY } from "./episodeLinkHistoryQuery"

// TODO: Validate
export function EpisodeLinkHistoryUndoButton({
  entry,
}: {
  entry: EpisodeLinkHistoryOutput
}) {
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const queryClient = useQueryClient()
  const ignored = entry.kind === "ignored"
  const absent = entry.kind === "absent"

  const undoMutation = useMutation({
    mutationFn: () => {
      if (absent) {
        return EpisodesService.adminQuickUnlinkEpisode({
          episodeId: entry.episode_id,
        })
      }
      if (ignored || !entry.tmdb_episode_id) {
        return EpisodesService.adminUnignoreEpisode({
          episodeId: entry.episode_id,
        })
      }
      return EpisodesService.adminUnlinkEpisodeFromTmdbEpisode({
        episodeId: entry.episode_id,
        tmdbEpisodeId: entry.tmdb_episode_id,
      })
    },
    onSuccess: () => {
      if (absent) {
        showSuccessToast("Episode no longer marked as absent from TMDB")
        return
      }
      showSuccessToast(
        ignored ? "Episode no longer ignored" : "Episode unlinked",
      )
    },
    onError: (error: unknown) =>
      handleError.call(
        showErrorToast,
        error as Parameters<typeof handleError>[0],
      ),
    onSettled: () => {
      queryClient.invalidateQueries({
        queryKey: EPISODE_LINK_HISTORY_QUERY_KEY,
      })
      queryClient.invalidateQueries({ queryKey: ["episodes"] })
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
