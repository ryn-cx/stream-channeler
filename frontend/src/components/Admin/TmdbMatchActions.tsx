// TODO: Validate
import { useMutation } from "@tanstack/react-query"
import { Check, CircleSlash, Hash, ListOrdered, ListTree } from "lucide-react"

import { EpisodesService } from "@/client"
import { Button } from "@/components/ui/button"
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"
import type { TmdbMatchRow } from "./tmdbMatchColumns"
import { useOpenEpisodeEditor } from "./tmdbMatchEditing"
import { useSettleTmdbMatch } from "./tmdbMatchesQuery"

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
  match: NonNullable<TmdbMatchRow["best_match"]>
  kind: "name" | "season_episode" | "absolute"
}) {
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const { settle, restore, reread } = useSettleTmdbMatch()

  const confirmMutation = useMutation({
    mutationFn: () =>
      EpisodesService.adminLinkEpisodeToTmdb({
        episodeId,
        canonicalEpisodeId: match.episode.id,
      }),
    onMutate: () => settle(episodeId),
    onSuccess: () =>
      showSuccessToast(
        `Linked to ${match.episode.name ?? "the suggested episode"}`,
      ),
    onError: (error: unknown, _variables, previous) => {
      restore(previous)
      handleError.call(
        showErrorToast,
        error as Parameters<typeof handleError>[0],
      )
    },
    onSettled: reread,
  })

  const icons = { name: Check, season_episode: Hash, absolute: ListOrdered }
  const labels = {
    name: "Name Match",
    season_episode: "Number Match",
    absolute: "Sequential Match",
  }
  const Icon = icons[kind]
  const label = labels[kind]

  return (
    <span className="mt-1 flex items-center gap-2">
      <Button
        variant="outline"
        size="sm"
        disabled={confirmMutation.isPending}
        title={`Link to ${match.episode.name ?? `the episode this ${label} offers`}`}
        onClick={() => confirmMutation.mutate()}
      >
        <Icon className="h-4 w-4" />
        {label}
      </Button>
      <span
        className="text-xs font-medium tabular-nums"
        style={{ color: `oklch(0.6 0.15 ${25 + match.similarity * 120})` }}
      >
        {Math.round(match.similarity * 100)}%
      </span>
    </span>
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
export function TmdbMatchActions({ episode }: { episode: TmdbMatchRow }) {
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const { settle, restore, reread } = useSettleTmdbMatch()
  const openEditor = useOpenEpisodeEditor()

  const absentMutation = useMutation({
    mutationFn: () =>
      EpisodesService.adminMarkEpisodeAbsentFromTmdb({
        episodeId: episode.episode.id,
      }),
    onMutate: () => settle(episode.episode.id),
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
        onClick={() => openEditor?.(episode)}
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
    </div>
  )
}
