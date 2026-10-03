// TODO: Validate
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { Unlink } from "lucide-react"

import { EpisodesService } from "@/client"
import { TooltipIconButton } from "@/components/Common/TooltipIconButton"
import { Label } from "@/components/ui/label"
import useAuth from "@/hooks/useAuth"
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"
import { entryFromEpisodeList, LinkedEpisodeCards } from "./LinkedEpisodeRow"

interface LinkedEpisodeLinksProps {
  episodeId: string
  enabled: boolean
}

// TODO: Validate
/**
 * Every website's row standing for this episode.
 *
 * The question a tmdb episode is opened with is the other way around from
 * the one a website's row is opened with: a row is settled by choosing which
 * episode it is of, and an episode is read by seeing which rows came to it.
 */
export function LinkedEpisodeLinks({
  episodeId,
  enabled,
}: LinkedEpisodeLinksProps) {
  const { user } = useAuth()
  const isAdmin = Boolean(user?.is_superuser)
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const queryClient = useQueryClient()
  const { data: episodes, isLoading } = useQuery({
    queryKey: ["episodes", episodeId, "linked"],
    queryFn: () => EpisodesService.getLinkedEpisodes({ episodeId }),
    enabled,
  })

  const unlinkMutation = useMutation({
    mutationFn: (droppedId: string) =>
      EpisodesService.adminUnlinkEpisodeFromTmdbEpisode({
        episodeId: droppedId,
        tmdbEpisodeId: episodeId,
      }),
    onSuccess: () => {
      showSuccessToast("Episode unlinked from this episode")
      queryClient.invalidateQueries({ queryKey: ["episodes"] })
      queryClient.invalidateQueries({ queryKey: ["admin-tmdb-choices"] })
    },
    onError: (error: unknown) =>
      handleError.call(
        showErrorToast,
        error as Parameters<typeof handleError>[0],
      ),
  })

  if (isLoading) {
    return (
      <p className="text-sm text-muted-foreground">
        Reading the linked episodes…
      </p>
    )
  }

  return (
    <div className="space-y-2">
      <Label>Linked Episodes</Label>
      {!episodes || episodes.length === 0 ? (
        <p className="text-sm text-muted-foreground">
          No episode is linked to this one.
        </p>
      ) : (
        <LinkedEpisodeCards
          entries={episodes.map(entryFromEpisodeList)}
          renderUnlink={
            isAdmin
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
