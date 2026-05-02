// TODO: Validate
import { useMutation } from "@tanstack/react-query"
import { useParams } from "@tanstack/react-router"
import { useState } from "react"

import { OpenAPI } from "@/client"
import { request } from "@/client/core/request"
import { DeleteConfirmContent } from "@/components/Common/DeleteConfirmContent"
import { DeleteIconTrigger } from "@/components/Common/DeleteIconTrigger"
import { Dialog } from "@/components/ui/dialog"
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"

import type { EpisodeTableData } from "./episodeColumns"

type EpisodesData = Array<EpisodeTableData>

interface DeleteEpisodeProps {
  episode: EpisodeTableData
}

const DeleteEpisode = ({ episode }: DeleteEpisodeProps) => {
  const { seasonKey } = useParams({ strict: false })
  const [isOpen, setIsOpen] = useState(false)
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const queryKey = ["seasons", seasonKey, "episodes"]

  const mutation = useMutation({
    mutationFn: (episodeId: string) =>
      request(OpenAPI, {
        method: "DELETE",
        url: "/api/v1/episodes/{episode_id}",
        path: { episode_id: episodeId },
      }),
    onMutate: async (_episodeKey, context) => {
      await context.client.cancelQueries({ queryKey })
      const previous = context.client.getQueryData<EpisodesData>(queryKey)

      context.client.setQueryData<EpisodesData>(queryKey, (old) =>
        old!.filter((e) => e.key !== episode.key),
      )

      return { previous }
    },
    onSuccess: () => {
      showSuccessToast("Episode deleted successfully")
      setIsOpen(false)
    },
    onError: (error, _episodeKey, onMutateResult, context) => {
      context.client.setQueryData(queryKey, onMutateResult?.previous)
      handleError.call(showErrorToast, error as any)
    },
    onSettled: (_data, _error, _variables, _onMutateResult, context) =>
      context.client.invalidateQueries({ queryKey }),
  })

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      <DeleteIconTrigger tooltip="Delete episode" />
      <DeleteConfirmContent
        title="Delete Episode"
        description={
          <>
            All data associated with this episode will be{" "}
            <strong>permanently deleted.</strong> Are you sure? You will not be
            able to undo this action.
          </>
        }
        isPending={mutation.isPending}
        onSubmit={() => mutation.mutate(episode.id)}
      />
    </Dialog>
  )
}

export default DeleteEpisode
