// TODO: Validate
import { useMutation, useQueries, useQueryClient } from "@tanstack/react-query"
import { Check, Eye, Unlink } from "lucide-react"

import {
  type EpisodeOutput,
  EpisodesService,
  TmdbEpisodesService,
} from "@/client"
import { TmdbLinkPicker } from "@/components/Admin/EpisodeTmdbLinkMenu"
import { TooltipIconButton } from "@/components/Common/TooltipIconButton"
import { Button } from "@/components/ui/button"
import { Label } from "@/components/ui/label"
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"
import { entryFromEpisodeRecord, LinkedEpisodeCards } from "./LinkedEpisodeRow"

interface TmdbEpisodeListProps {
  episodeId: string
  tmdbEpisodeIds: string[]
  enabled: boolean
  /** Whether the rows have the control that takes one off. */
  editable?: boolean
  /** Whether the episode has been set aside, which is why it reaches TMDB at all. */
  ignored?: boolean
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
  ignored = false,
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
      {ignored ? (
        <p className="text-sm text-muted-foreground">
          This episode is ignored, so it is never matched to a TMDB episode.
        </p>
      ) : null}
      {tmdbEpisodeIds.length === 0 ? (
        !ignored && (
          <p className="text-sm text-muted-foreground">
            Linked to no tmdb episode.
          </p>
        )
      ) : (
        <LinkedEpisodeCards
          entries={linked.map(entryFromEpisodeRecord)}
          showSource={false}
          renderUnlink={
            editable
              ? (entry) => (
                  <TooltipIconButton
                    label="Unlink Episode"
                    icon={<Unlink />}
                    className="bg-blue-900 text-white hover:bg-blue-900/90 dark:bg-blue-500/60 dark:hover:bg-blue-500/50"
                    disabled={unlinkMutation.isPending}
                    onClick={() => unlinkMutation.mutate(entry.record.id)}
                  />
                )
              : undefined
          }
        />
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
  /** Whether the episode has been set aside, which leaves nothing to choose. */
  ignored?: boolean
  /** Called once the episode is no longer set aside, so the picker can be read. */
  onUnignored?: () => void
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
  ignored = false,
  onUnignored,
  onVerified,
  onLinksChanged,
}: TmdbEpisodeControlsProps) {
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const queryClient = useQueryClient()

  const unignoreMutation = useMutation({
    mutationFn: () => EpisodesService.adminUnignoreEpisode({ episodeId }),
    onSuccess: () => {
      showSuccessToast("Episode no longer ignored")
      onUnignored?.()
      queryClient.invalidateQueries({ queryKey: ["episodes"] })
      queryClient.invalidateQueries({ queryKey: ["episode-information"] })
      queryClient.invalidateQueries({ queryKey: ["admin-tmdb-choices"] })
    },
    onError: (error: unknown) =>
      handleError.call(
        showErrorToast,
        error as Parameters<typeof handleError>[0],
      ),
  })

  const verifyMutation = useMutation({
    mutationFn: () => EpisodesService.adminVerifyTmdbLink({ episodeId }),
    onSuccess: () => {
      showSuccessToast("TMDB link verified and locked")
      onVerified?.()
      queryClient.invalidateQueries({ queryKey: ["episodes"] })
      queryClient.invalidateQueries({ queryKey: ["admin-tmdb-choices"] })
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
      {ignored ? (
        <Button
          type="button"
          variant="outline"
          size="sm"
          disabled={unignoreMutation.isPending}
          onClick={() => unignoreMutation.mutate()}
        >
          <Eye className="h-4 w-4" />
          Stop ignoring
        </Button>
      ) : null}
      {enabled && !ignored ? (
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
