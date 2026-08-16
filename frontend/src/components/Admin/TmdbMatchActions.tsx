// TODO: Validate
import { useMutation } from "@tanstack/react-query"
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
import { TMDB_MATCHES_QUERY_KEY, useSettleTmdbMatch } from "./tmdbMatchesQuery"

// TODO: Validate
/**
 * Take the suggestion one of the TMDB columns is offering.
 *
 * Beneath the suggestion rather than in the actions column, because the two
 * suggestions are two different episodes and a button away from the episode it
 * links to says nothing about which one it takes. They are the same episode
 * often enough that most rows are settled either way, and where they differ it
 * is the summary above the button that says which to trust.
 */
export function TmdbMatchConfirmButton({
  episodeId,
  match,
  kind,
}: {
  episodeId: string
  match: NonNullable<UnmatchedEpisodeOutput["best_match"]>
  kind: "name" | "number"
}) {
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const { settle, restore, reread } = useSettleTmdbMatch()

  const confirmMutation = useMutation({
    mutationFn: () =>
      EpisodesService.adminLinkEpisodeToTmdb({
        episodeId,
        canonicalEpisodeId: match.canonical_episode_id,
      }),
    onMutate: () => settle(episodeId),
    onSuccess: () =>
      showSuccessToast(`Linked to ${match.name ?? "the suggested episode"}`),
    onError: (error: unknown, _variables, previous) => {
      restore(previous)
      handleError.call(
        showErrorToast,
        error as Parameters<typeof handleError>[0],
      )
    },
    onSettled: reread,
  })

  const Icon = kind === "name" ? Check : Hash
  const label = kind === "name" ? "Name Match" : "Number Match"

  return (
    <Button
      variant="outline"
      size="sm"
      className="mt-1"
      disabled={confirmMutation.isPending}
      title={`Link to ${match.name ?? `the episode matched by ${kind}`}`}
      onClick={() => confirmMutation.mutate()}
    >
      <Icon className="h-4 w-4" />
      {label}
    </Button>
  )
}

// TODO: Validate
/**
 * Settle one row by going and choosing, or by saying there is nothing to choose.
 *
 * Choosing opens the same picker an episode's own page carries, so the one
 * place that knows how to offer TMDB episodes and link one is the place doing
 * it here too. Taking one of the two suggestions is done from the column
 * offering it instead, by `TmdbMatchConfirmButton`.
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
  const { settle, restore, reread } = useSettleTmdbMatch()
  const [isPicking, setIsPicking] = useState(false)

  const absentMutation = useMutation({
    mutationFn: () =>
      EpisodesService.adminMarkEpisodeAbsentFromTmdb({ episodeId: episode.id }),
    onMutate: () => settle(episode.id),
    onSuccess: () => showSuccessToast("Marked as not on TMDB"),
    onError: (error: unknown, _variables, previous) => {
      restore(previous)
      handleError.call(
        showErrorToast,
        error as Parameters<typeof handleError>[0],
      )
    },
    onSettled: reread,
  })

  return (
    <div className="flex items-center gap-1">
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
