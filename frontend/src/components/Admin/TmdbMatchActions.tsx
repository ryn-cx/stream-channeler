// TODO: Validate
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { Check, CircleSlash, Hash, ListTree } from "lucide-react"
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
 * Settle one row: take either suggestion, or go and choose.
 *
 * The two suggestions are the two ways a row can be read - the episode TMDB
 * names the same, and the one it numbers the same - and each has a button of
 * its own so the one that is right can be taken without opening anything. They
 * are the same episode often enough that most rows are settled either way, and
 * where they differ the columns beside them are what says which to trust.
 *
 * Choosing opens the same picker an episode's own page carries, so the one
 * place that knows how to offer TMDB episodes and link one is the place doing
 * it here too.
 *
 * A settled episode is no longer waiting on anybody, so the row leaves the table
 * as soon as any way of settling it succeeds.
 */
export function TmdbMatchActions({
  episode,
}: {
  episode: UnmatchedEpisodeOutput
}) {
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const queryClient = useQueryClient()
  const [isPicking, setIsPicking] = useState(false)

  const nameMatch = episode.best_match
  const numberMatch = episode.number_match

  const confirmMutation = useMutation({
    mutationFn: ({ canonicalEpisodeId }: { canonicalEpisodeId: string }) =>
      EpisodesService.adminLinkEpisodeToTmdb({
        episodeId: episode.id,
        canonicalEpisodeId,
      }),
    onSuccess: (_result, { canonicalEpisodeId }) => {
      const linked =
        canonicalEpisodeId === numberMatch?.canonical_episode_id
          ? numberMatch
          : nameMatch
      showSuccessToast(`Linked to ${linked?.name ?? "the suggested episode"}`)
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
        disabled={!nameMatch || confirmMutation.isPending}
        title={
          nameMatch
            ? `Link to ${nameMatch.name ?? "the episode matched by name"}`
            : "Nothing was matched by name for this episode"
        }
        onClick={() =>
          nameMatch &&
          confirmMutation.mutate({
            canonicalEpisodeId: nameMatch.canonical_episode_id,
          })
        }
      >
        <Check className="h-4 w-4" />
        Name Match
      </Button>
      <Button
        variant="outline"
        size="sm"
        disabled={!numberMatch || confirmMutation.isPending}
        title={
          numberMatch
            ? `Link to ${numberMatch.name ?? "the episode matched by number"}`
            : "Nothing was matched by number for this episode"
        }
        onClick={() =>
          numberMatch &&
          confirmMutation.mutate({
            canonicalEpisodeId: numberMatch.canonical_episode_id,
          })
        }
      >
        <Hash className="h-4 w-4" />
        Number Match
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
