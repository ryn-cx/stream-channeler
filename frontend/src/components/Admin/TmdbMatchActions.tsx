// TODO: Validate
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { Check, CircleSlash, ListTree } from "lucide-react"
import { useState } from "react"

import type { UnmatchedEpisodeOutput } from "@/client"
import { EpisodesService } from "@/client"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"
import { TmdbLinkPicker } from "./EpisodeTmdbLinkMenu"
import { TMDB_MATCHES_QUERY_KEY } from "./tmdbMatchesQuery"

// TODO: Validate
/**
 * Settle one row: take the suggestion, or go and choose.
 *
 * Confirming writes the guess the table is already showing, which is the whole
 * of what most rows need. Choosing opens the same picker an episode's own page
 * carries, so the one place that knows how to offer TMDB episodes and link one
 * is the place doing it here too.
 *
 * A settled episode is no longer waiting on anybody, so the row leaves the table
 * as soon as either way of settling it succeeds.
 */
export function TmdbMatchActions({
  episode,
}: {
  episode: UnmatchedEpisodeOutput
}) {
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const queryClient = useQueryClient()
  const [isPicking, setIsPicking] = useState(false)

  const bestMatch = episode.best_match

  const confirmMutation = useMutation({
    mutationFn: (canonicalEpisodeId: string) =>
      EpisodesService.adminLinkEpisodeToTmdb({
        episodeId: episode.id,
        canonicalEpisodeId,
      }),
    onSuccess: () => {
      showSuccessToast(
        `Linked to ${bestMatch?.name ?? "the suggested episode"}`,
      )
      queryClient.invalidateQueries({ queryKey: TMDB_MATCHES_QUERY_KEY })
      queryClient.invalidateQueries({ queryKey: ["admin-tmdb-choices"] })
    },
    onError: (error: unknown) =>
      handleError.call(
        showErrorToast,
        error as Parameters<typeof handleError>[0],
      ),
  })

  const absentMutation = useMutation({
    mutationFn: () =>
      EpisodesService.adminMarkEpisodeAbsentFromTmdb({ episodeId: episode.id }),
    onSuccess: () => {
      showSuccessToast("Marked as not on TMDB")
      queryClient.invalidateQueries({ queryKey: TMDB_MATCHES_QUERY_KEY })
      queryClient.invalidateQueries({ queryKey: ["admin-tmdb-choices"] })
    },
    onError: (error: unknown) =>
      handleError.call(
        showErrorToast,
        error as Parameters<typeof handleError>[0],
      ),
  })

  return (
    <div className="flex items-center gap-1">
      <Button
        variant="outline"
        size="sm"
        disabled={!bestMatch || confirmMutation.isPending}
        title={
          bestMatch
            ? `Link to ${bestMatch.name ?? "the suggested episode"}`
            : "Nothing was suggested for this episode"
        }
        onClick={() =>
          bestMatch && confirmMutation.mutate(bestMatch.canonical_episode_id)
        }
      >
        <Check className="h-4 w-4" />
        Confirm
      </Button>
      <Button
        variant="outline"
        size="sm"
        onClick={() => setIsPicking(true)}
        title="Choose a TMDB episode"
      >
        <ListTree className="h-4 w-4" />
        Pick
      </Button>
      <Button
        variant="outline"
        size="sm"
        disabled={absentMutation.isPending}
        title="Settle this as an episode TMDB has no record of"
        onClick={() => absentMutation.mutate()}
      >
        <CircleSlash className="h-4 w-4" />
        Not on TMDB
      </Button>

      {/*
        The picker reads every episode of every title the show is linked to, so
        it is left to the dialog to mount it: rendering one per row would ask
        for the whole catalogue just to draw the table.
      */}
      <Dialog open={isPicking} onOpenChange={setIsPicking}>
        <DialogContent className="sm:max-w-3xl max-h-[85vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>
              {episode.show_name ?? "Unnamed show"} — TMDB episode link
            </DialogTitle>
          </DialogHeader>
          <TmdbLinkPicker
            episodeId={episode.id}
            name={episode.name}
            seasonNumber={episode.season_number}
            episodeNumber={episode.episode_number}
            informationQueryKey={TMDB_MATCHES_QUERY_KEY}
            onLinked={() => setIsPicking(false)}
          />
        </DialogContent>
      </Dialog>
    </div>
  )
}
