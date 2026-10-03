// TODO: Validate
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { Eye, EyeOff } from "lucide-react"

import { EpisodesService } from "@/client"
import { TooltipIconButton } from "@/components/Common/TooltipIconButton"
import { queryHasRow } from "@/components/Common/useDeleteTableRow"
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"

import type { EpisodeTableData } from "./columns"

interface ToggleIgnoredEpisodeProps {
  episode: EpisodeTableData
}

// TODO: Validate
const ToggleIgnoredEpisode = ({ episode }: ToggleIgnoredEpisodeProps) => {
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const queryClient = useQueryClient()
  const ignored = episode.ignored_at !== null

  const mutation = useMutation({
    mutationFn: () =>
      ignored
        ? EpisodesService.adminUnignoreEpisode({ episodeId: episode.id })
        : EpisodesService.adminIgnoreEpisode({ episodeId: episode.id }),
    onSuccess: () =>
      showSuccessToast(
        ignored ? "Episode no longer ignored" : "Episode ignored",
      ),
    onError: (error: unknown) =>
      handleError.call(
        showErrorToast,
        error as Parameters<typeof handleError>[0],
      ),
    onSettled: () =>
      queryClient.invalidateQueries({ predicate: queryHasRow(episode.id) }),
  })

  return (
    <TooltipIconButton
      label={ignored ? "Stop Ignoring Episode" : "Ignore Episode"}
      icon={ignored ? <Eye /> : <EyeOff />}
      disabled={mutation.isPending}
      onClick={() => mutation.mutate()}
    />
  )
}

export default ToggleIgnoredEpisode
