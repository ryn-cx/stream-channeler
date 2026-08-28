// TODO: Validate
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { Link } from "@tanstack/react-router"
import { Unlink } from "lucide-react"

import { EpisodesService } from "@/client"
import { TooltipIconButton } from "@/components/Common/TooltipIconButton"
import { Label } from "@/components/ui/label"
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"
import EditEpisode from "./Edit"

interface NonCanonicalEpisodeLinksProps {
  episodeId: string
  enabled: boolean
}

// TODO: Validate
/**
 * Every website's row standing for this episode.
 *
 * The question a canonical episode is opened with is the other way around from
 * the one a website's row is opened with: a row is settled by choosing which
 * episode it is of, and an episode is read by seeing which rows came to it.
 */
export function NonCanonicalEpisodeLinks({
  episodeId,
  enabled,
}: NonCanonicalEpisodeLinksProps) {
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const queryClient = useQueryClient()
  const { data: episodes, isLoading } = useQuery({
    queryKey: ["episodes", episodeId, "non-canonical"],
    queryFn: () => EpisodesService.getNonCanonicalEpisodes({ episodeId }),
    enabled,
  })

  const unlinkMutation = useMutation({
    mutationFn: (droppedId: string) =>
      EpisodesService.adminUnlinkEpisodeFromCanonical({
        episodeId: droppedId,
        canonicalEpisodeId: episodeId,
      }),
    onSuccess: () => {
      showSuccessToast("Episode unlinked from this episode")
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
        <div className="rounded-lg border">
          {episodes.map((linked) => (
            <div
              key={linked.id}
              className="flex items-center gap-3 border-b px-3 py-2 text-sm last:border-b-0"
            >
              <span className="flex-1 whitespace-normal wrap-break-word">
                <Link
                  to="/episodes"
                  search={{ season_id: linked.season_id }}
                  className="hover:underline"
                >
                  {linked.name ?? "Unnamed"}
                </Link>
                <span className="block text-xs text-muted-foreground">
                  {linked.source_name ?? linked.plugin_name ?? linked.key}
                </span>
              </span>
              <EditEpisode episode={linked} />
              <TooltipIconButton
                label="Unlink Episode"
                icon={<Unlink />}
                size="sm"
                disabled={unlinkMutation.isPending}
                onClick={() => unlinkMutation.mutate(linked.id)}
              />
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
