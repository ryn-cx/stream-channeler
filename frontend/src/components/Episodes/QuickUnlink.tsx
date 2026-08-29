// TODO: Validate
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { Unlink } from "lucide-react"

import { EpisodesService } from "@/client"
import { TooltipIconButton } from "@/components/Common/TooltipIconButton"
import { queryHasRow } from "@/components/Common/useDeleteTableRow"
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"

import type { EpisodeTableData } from "./columns"

interface QuickUnlinkEpisodeProps {
  episode: EpisodeTableData
}

// TODO: Validate
const QuickUnlinkEpisode = ({ episode }: QuickUnlinkEpisodeProps) => {
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const queryClient = useQueryClient()

  const mutation = useMutation({
    mutationFn: () =>
      EpisodesService.adminQuickUnlinkEpisode({ episodeId: episode.id }),
    onSuccess: () => showSuccessToast("Episode unlinked"),
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
      label="Unlink Episode"
      icon={<Unlink />}
      disabled={mutation.isPending}
      onClick={() => mutation.mutate()}
    />
  )
}

export default QuickUnlinkEpisode
