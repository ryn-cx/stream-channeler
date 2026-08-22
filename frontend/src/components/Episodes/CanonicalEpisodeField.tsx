// TODO: Validate
import { useMutation, useQueries, useQueryClient } from "@tanstack/react-query"
import { Check, X } from "lucide-react"

import {
  type CanonicalEpisodeOutput,
  CanonicalEpisodesService,
  EpisodesService,
} from "@/client"
import { TmdbLinkPicker } from "@/components/Admin/EpisodeTmdbLinkMenu"
import { Button } from "@/components/ui/button"
import { Label } from "@/components/ui/label"
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"

interface CanonicalEpisodeFieldProps {
  episodeId: string
  canonicalEpisodeIds: string[]
  name: string | null
  seasonNumber: number | null
  episodeNumber: number | null
  canonicalEpisodeLocked: boolean
  /** Only asked for while the form is open, since each is a query of its own. */
  enabled: boolean
  /** Called once the links have been settled, so a form holding the row's own
   * copy of the lock can be brought in line with what was just written. */
  onVerified?: () => void
}

// TODO: Validate
function CanonicalEpisodeName({
  episode,
}: {
  episode: CanonicalEpisodeOutput
}) {
  return (
    <span className="flex-1 whitespace-normal wrap-break-word">
      {episode.name ?? "Unnamed"}
      <span className="block text-xs text-muted-foreground">
        {episode.key}
        {episode.episode_number === null || episode.episode_number === undefined
          ? ""
          : ` — episode ${episode.episode_number}`}
      </span>
    </span>
  )
}

// TODO: Validate
/**
 * Which episodes this row stands for, and the choosing of another.
 *
 * A website runs two episodes together in one listing often enough - a
 * double-length first airing, a recap paired with the episode it recaps - that
 * choosing here adds to what the row already stands for rather than replacing
 * it. Taking one off is the X beside it.
 *
 * The choosing is the same picker the matching screens use, so the one place
 * that knows how to offer TMDB episodes and link one is the place doing it here
 * too, and a link chosen here reads exactly as one chosen there.
 *
 * The links are written as soon as they are chosen rather than with the rest of
 * the form: they are rows of their own, and what they drag along is not
 * something a write of the episode's own columns does.
 */
export function CanonicalEpisodeField({
  episodeId,
  canonicalEpisodeIds,
  name,
  seasonNumber,
  episodeNumber,
  canonicalEpisodeLocked,
  enabled,
  onVerified,
}: CanonicalEpisodeFieldProps) {
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const queryClient = useQueryClient()

  const linkedQueries = useQueries({
    queries: canonicalEpisodeIds.map((canonicalEpisodeId) => ({
      queryKey: ["canonical-episode", canonicalEpisodeId],
      queryFn: () =>
        CanonicalEpisodesService.getCanonicalEpisodeById({
          canonicalEpisodeId,
        }),
      enabled,
    })),
  })
  const linked = linkedQueries
    .map((query) => query.data)
    .filter((episode) => episode !== undefined)

  const unlinkMutation = useMutation({
    mutationFn: (droppedId: string) =>
      EpisodesService.adminUnlinkEpisodeFromCanonical({
        episodeId,
        canonicalEpisodeId: droppedId,
      }),
    onSuccess: () => {
      showSuccessToast("Episode unlinked from TMDB episode")
      queryClient.invalidateQueries({ queryKey: ["episodes"] })
      queryClient.invalidateQueries({ queryKey: ["admin-tmdb-choices"] })
    },
    onError: (error: unknown) =>
      handleError.call(
        showErrorToast,
        error as Parameters<typeof handleError>[0],
      ),
  })

  const verifyMutation = useMutation({
    mutationFn: () => EpisodesService.adminVerifyCanonicalLink({ episodeId }),
    onSuccess: () => {
      showSuccessToast("Canonical link verified and locked")
      onVerified?.()
      queryClient.invalidateQueries({ queryKey: ["episodes"] })
      queryClient.invalidateQueries({ queryKey: ["admin-tmdb-choices"] })
      queryClient.invalidateQueries({
        queryKey: ["admin-duplicated-canonical-episodes"],
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
      <Label>Canonical Episodes</Label>
      {canonicalEpisodeIds.length === 0 ? (
        <p className="text-sm text-muted-foreground">
          Linked to no canonical episode.
        </p>
      ) : (
        <div className="rounded-lg border">
          {canonicalEpisodeIds.map((canonicalEpisodeId) => {
            const episode = linked.find(
              (each) => each.id === canonicalEpisodeId,
            )
            return (
              <div
                key={canonicalEpisodeId}
                className="flex items-center gap-3 border-b px-3 py-2 text-sm last:border-b-0"
              >
                {episode ? (
                  <CanonicalEpisodeName episode={episode} />
                ) : (
                  <span className="flex-1 text-muted-foreground">
                    Reading the linked episode…
                  </span>
                )}
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  className="shrink-0"
                  title="Unlink from this canonical episode"
                  disabled={unlinkMutation.isPending}
                  onClick={() => unlinkMutation.mutate(canonicalEpisodeId)}
                >
                  <X className="h-4 w-4" />
                </Button>
              </div>
            )
          })}
        </div>
      )}
      {canonicalEpisodeIds.length > 0 ? (
        <Button
          type="button"
          variant={canonicalEpisodeLocked ? "outline" : "default"}
          size="sm"
          disabled={canonicalEpisodeLocked || verifyMutation.isPending}
          onClick={() => verifyMutation.mutate()}
        >
          <Check className="h-4 w-4" />
          {canonicalEpisodeLocked
            ? "Link verified and locked"
            : "Verify and lock link"}
        </Button>
      ) : null}
      {enabled ? (
        <TmdbLinkPicker
          episodeId={episodeId}
          name={name}
          seasonNumber={seasonNumber}
          episodeNumber={episodeNumber}
          informationQueryKey={["episodes"]}
        />
      ) : null}
    </div>
  )
}
