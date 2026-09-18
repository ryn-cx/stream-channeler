// TODO: Validate
import { useMutation, useQueries, useQueryClient } from "@tanstack/react-query"
import { Check, X } from "lucide-react"

import {
  type EpisodeOutput,
  EpisodesService,
  TmdbEpisodesService,
} from "@/client"
import { TmdbLinkPicker } from "@/components/Admin/EpisodeTmdbLinkMenu"
import { TmdbEpisodeRow } from "@/components/Admin/TmdbEpisodeRow"
import { Button } from "@/components/ui/button"
import { Label } from "@/components/ui/label"
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"

interface TmdbEpisodeListProps {
  episodeId: string
  tmdbEpisodeIds: string[]
  enabled: boolean
  /** Whether the rows carry the control that takes one off. */
  editable?: boolean
  onLinksChanged?: (episode: EpisodeOutput) => void
}

// TODO: Validate
/**
 * Which episodes this row stands for.
 *
 * Read by anybody, since what a listing is of is as much a part of the episode
 * as its name. Only an admin is given the control that takes one off, which is
 * the whole of the difference between the two readings.
 */
export function TmdbEpisodeList({
  episodeId,
  tmdbEpisodeIds,
  enabled,
  editable = false,
  onLinksChanged,
}: TmdbEpisodeListProps) {
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const queryClient = useQueryClient()

  const linkedQueries = useQueries({
    queries: tmdbEpisodeIds.map((tmdbEpisodeId) => ({
      queryKey: ["tmdb-episode", tmdbEpisodeId],
      queryFn: () =>
        TmdbEpisodesService.getTmdbEpisodeById({
          tmdbEpisodeId,
        }),
      enabled,
    })),
  })
  const linked = linkedQueries
    .map((query) => query.data)
    .filter((record) => record !== undefined)

  const unlinkMutation = useMutation({
    mutationFn: (droppedId: string) =>
      EpisodesService.adminUnlinkEpisodeFromTmdbEpisode({
        episodeId,
        tmdbEpisodeId: droppedId,
      }),
    onSuccess: (unlinked) => {
      showSuccessToast("Episode unlinked from TMDB episode")
      queryClient.invalidateQueries({ queryKey: ["episodes"] })
      queryClient.invalidateQueries({ queryKey: ["admin-tmdb-choices"] })
      onLinksChanged?.(unlinked)
    },
    onError: (error: unknown) =>
      handleError.call(
        showErrorToast,
        error as Parameters<typeof handleError>[0],
      ),
  })

  return (
    <div className="space-y-2">
      <Label>TMDB Episodes</Label>
      {tmdbEpisodeIds.length === 0 ? (
        <p className="text-sm text-muted-foreground">
          Linked to no tmdb episode.
        </p>
      ) : (
        <div className="rounded-lg border">
          {tmdbEpisodeIds.map((tmdbEpisodeId) => {
            const record = linked.find(
              (each) => each.episode.id === tmdbEpisodeId,
            )
            const unlink = editable ? (
              <Button
                type="button"
                variant="ghost"
                size="icon"
                className="shrink-0"
                title="Unlink from this tmdb episode"
                disabled={unlinkMutation.isPending}
                onClick={() => unlinkMutation.mutate(tmdbEpisodeId)}
              >
                <X className="h-4 w-4" />
              </Button>
            ) : null
            if (!record) {
              return (
                <div
                  key={tmdbEpisodeId}
                  className="flex items-center gap-3 border-b px-3 py-2 text-sm last:border-b-0"
                >
                  <span className="flex-1 text-muted-foreground">
                    Reading the linked episode…
                  </span>
                  {unlink}
                </div>
              )
            }
            return (
              <TmdbEpisodeRow
                key={tmdbEpisodeId}
                record={record}
                absoluteNumber={record.absolute_number}
                trailing={unlink}
              />
            )
          })}
        </div>
      )}
    </div>
  )
}

interface TmdbEpisodeControlsProps {
  episodeId: string
  seasonNumber: number | null
  episodeNumber: number | null
  tmdbEpisodeValidatedAt: string | null | undefined
  tmdbEpisodeNote: string | null | undefined
  /** Whether there is a link to settle, since there is nothing to lock without one. */
  hasLinks: boolean
  enabled: boolean
  /** Called once the links have been settled, so a form holding the row's own
   * copy of the lock can be brought in line with what was just written. */
  onVerified?: () => void
  onLinksChanged?: (episode: EpisodeOutput) => void
}

// TODO: Validate
/**
 * The settling of which episodes a row stands for.
 *
 * A website runs two episodes together in one listing often enough - a
 * double-length first airing, a recap paired with the episode it recaps - that
 * choosing here adds to what the row already stands for rather than replacing
 * it. Taking one off is the X beside it in the list above.
 *
 * The choosing is the same picker the matching screens use, so the one place
 * that knows how to offer TMDB episodes and link one is the place doing it here
 * too, and a link chosen here reads exactly as one chosen there.
 *
 * The links are written as soon as they are chosen rather than with the rest of
 * the form: they are rows of their own, and what they drag along is not
 * something a write of the episode's own columns does.
 */
export function TmdbEpisodeControls({
  episodeId,
  seasonNumber,
  episodeNumber,
  tmdbEpisodeValidatedAt,
  tmdbEpisodeNote,
  hasLinks,
  enabled,
  onVerified,
  onLinksChanged,
}: TmdbEpisodeControlsProps) {
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const queryClient = useQueryClient()

  const verifyMutation = useMutation({
    mutationFn: () => EpisodesService.adminVerifyTmdbLink({ episodeId }),
    onSuccess: () => {
      showSuccessToast("TMDB link verified and locked")
      onVerified?.()
      queryClient.invalidateQueries({ queryKey: ["episodes"] })
      queryClient.invalidateQueries({ queryKey: ["admin-tmdb-choices"] })
      queryClient.invalidateQueries({
        queryKey: ["admin-duplicated-tmdb-episodes"],
      })
    },
    onError: (error: unknown) =>
      handleError.call(
        showErrorToast,
        error as Parameters<typeof handleError>[0],
      ),
  })

  const verifyLinkMutation = useMutation({
    mutationFn: () =>
      EpisodesService.updateEpisode({
        episodeId,
        requestBody: {
          tmdb_episode_note: tmdbEpisodeNote
            ? `Manual: Verified - ${tmdbEpisodeNote}`
            : "Manual: Verified",
          tmdb_episode_validated_at: new Date().toISOString(),
        },
      }),
    onSuccess: (updated) => {
      showSuccessToast("TMDB link verified and locked")
      onLinksChanged?.(updated)
      queryClient.invalidateQueries({ queryKey: ["episodes"] })
      queryClient.invalidateQueries({ queryKey: ["admin-tmdb-choices"] })
      queryClient.invalidateQueries({
        queryKey: ["admin-duplicated-tmdb-episodes"],
      })
    },
    onError: (error: unknown) =>
      handleError.call(
        showErrorToast,
        error as Parameters<typeof handleError>[0],
      ),
  })

  return (
    <div className="space-y-2">
      {hasLinks ? (
        <Button
          type="button"
          variant={tmdbEpisodeValidatedAt ? "outline" : "default"}
          size="sm"
          disabled={Boolean(tmdbEpisodeValidatedAt) || verifyMutation.isPending}
          onClick={() => verifyMutation.mutate()}
        >
          <Check className="h-4 w-4" />
          {tmdbEpisodeValidatedAt ? "Link validated" : "Validate link"}
        </Button>
      ) : null}
      {enabled ? (
        <TmdbLinkPicker
          episodeId={episodeId}
          seasonNumber={seasonNumber}
          episodeNumber={episodeNumber}
          informationQueryKey={["episodes"]}
          onLinksChanged={onLinksChanged}
        />
      ) : null}
      {hasLinks ? (
        <div>
          <Button
            type="button"
            variant="outline"
            size="sm"
            disabled={verifyLinkMutation.isPending}
            onClick={() => verifyLinkMutation.mutate()}
          >
            <Check className="h-4 w-4" />
            Verify Link
          </Button>
        </div>
      ) : null}
    </div>
  )
}
