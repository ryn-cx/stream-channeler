// TODO: Validate
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { Check, List, X } from "lucide-react"
import { useState } from "react"

import {
  type ApiError,
  type EpisodeOutput,
  EpisodesService,
  type MediaType,
  type UnmatchedEpisodeOutput,
} from "@/client"
import { Button } from "@/components/ui/button"
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"
import { TmdbEpisodePickerDialog } from "./TmdbEpisodePickerDialog"
import { TMDB_MATCHES_QUERY_KEY } from "./tmdbMatchesQuery"

/** The rows put back when the server refuses what was already taken off the table. */
interface RemovedRows {
  previousRows?: UnmatchedEpisodeOutput[]
}

// TODO: Validate
/**
 * Settle which TMDB episode an episode is, or settle that it is none of them.
 *
 * The checkmark takes the match that is displayed, the list opens every TMDB
 * episode of the title to choose from when the closest one is not it, and the
 * cross holds the episode at the identifier its own website issued.
 */
export function TmdbMatchApproval({
  episode,
}: {
  episode: UnmatchedEpisodeOutput
}) {
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const [isPicking, setIsPicking] = useState(false)

  // An episode that has been settled is off the list whichever way it was
  // settled, so the row is taken out as the button is pressed rather than left
  // sitting there until the server has been asked and the table read back.
  // TODO: Validate
  const takeRowOff = async (): Promise<RemovedRows> => {
    await queryClient.cancelQueries({ queryKey: TMDB_MATCHES_QUERY_KEY })
    const previousRows = queryClient.getQueryData<UnmatchedEpisodeOutput[]>(
      TMDB_MATCHES_QUERY_KEY,
    )
    queryClient.setQueryData<UnmatchedEpisodeOutput[]>(
      TMDB_MATCHES_QUERY_KEY,
      (rows) => rows?.filter((row) => row.id !== episode.id),
    )
    setIsPicking(false)
    return { previousRows }
  }

  // TODO: Validate
  const putRowBack = (
    error: ApiError,
    _variables: unknown,
    context: RemovedRows | undefined,
  ) => {
    if (context?.previousRows) {
      queryClient.setQueryData(TMDB_MATCHES_QUERY_KEY, context.previousRows)
    }
    handleError.call(showErrorToast, error)
  }

  // TODO: Validate
  const settleQueries = () =>
    queryClient.invalidateQueries({ queryKey: TMDB_MATCHES_QUERY_KEY })

  // Taking the match that was offered and going and finding one are recorded
  // apart, so a link says which of the two it was when it is read back.
  const linkMutation = useMutation({
    mutationFn: ({
      tmdbEpisodeId,
      mediaType,
      selected,
    }: {
      tmdbEpisodeId: number
      mediaType?: MediaType
      selected: boolean
    }) =>
      EpisodesService.adminLinkEpisodeToTmdb({
        episodeId: episode.id,
        requestBody: {
          tmdb_episode_id: tmdbEpisodeId,
          media_type: mediaType ?? null,
          selected,
        },
      }),
    onMutate: takeRowOff,
    onSuccess: () => showSuccessToast("Episode linked to TMDB"),
    onError: putRowBack,
    onSettled: settleQueries,
  })

  const noMatchMutation = useMutation<
    EpisodeOutput,
    ApiError,
    void,
    RemovedRows
  >({
    mutationFn: () =>
      EpisodesService.adminMarkEpisodeNoTmdbMatch({ episodeId: episode.id }),
    onMutate: takeRowOff,
    onSuccess: () => showSuccessToast("Episode marked as having no TMDB match"),
    onError: putRowBack,
    onSettled: settleQueries,
  })

  const isSaving = linkMutation.isPending || noMatchMutation.isPending

  return (
    <div className="flex items-center justify-end gap-2">
      <Button
        variant="outline"
        size="icon-sm"
        aria-label="Approve closest match"
        title="Approve closest match"
        disabled={!episode.best_match || isSaving}
        onClick={() => {
          if (episode.best_match) {
            linkMutation.mutate({
              tmdbEpisodeId: episode.best_match.tmdb_episode_id,
              selected: false,
            })
          }
        }}
      >
        <Check className="text-green-500" />
      </Button>
      <Button
        variant="outline"
        size="icon-sm"
        aria-label="Choose another episode"
        title="Choose another episode"
        disabled={isSaving}
        onClick={() => setIsPicking(true)}
      >
        <List />
      </Button>
      <Button
        variant="outline"
        size="icon-sm"
        aria-label="No TMDB match"
        title="No TMDB match — keep the episode as its own website has it"
        disabled={isSaving}
        onClick={() => noMatchMutation.mutate()}
      >
        <X className="text-destructive" />
      </Button>
      <TmdbEpisodePickerDialog
        episode={episode}
        isOpen={isPicking}
        onOpenChange={setIsPicking}
        onPick={(tmdbEpisodeId, mediaType) =>
          linkMutation.mutate({ tmdbEpisodeId, mediaType, selected: true })
        }
        isLinking={linkMutation.isPending}
      />
    </div>
  )
}
