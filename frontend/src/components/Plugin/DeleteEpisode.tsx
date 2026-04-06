// TODO: Validate
import { useMutation } from "@tanstack/react-query"
import { useParams } from "@tanstack/react-router"
import { Trash2 } from "lucide-react"
import { useState } from "react"
import { useForm } from "react-hook-form"

import { OpenAPI } from "@/client"
import { request } from "@/client/core/request"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { LoadingButton } from "@/components/ui/loading-button"
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip"
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
  const { handleSubmit } = useForm()
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

  const onSubmit = () => {
    mutation.mutate(episode.id)
  }

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      <Tooltip>
        <TooltipTrigger asChild>
          <DialogTrigger asChild>
            <Button variant="ghost">
              <Trash2 className="text-destructive" />
            </Button>
          </DialogTrigger>
        </TooltipTrigger>
        <TooltipContent>
          <p>Delete episode</p>
        </TooltipContent>
      </Tooltip>
      <DialogContent className="sm:max-w-md">
        <form onSubmit={handleSubmit(onSubmit)}>
          <DialogHeader>
            <DialogTitle>Delete Episode</DialogTitle>
            <DialogDescription>
              All data associated with this episode will be{" "}
              <strong>permanently deleted.</strong> Are you sure? You will not
              be able to undo this action.
            </DialogDescription>
          </DialogHeader>

          <DialogFooter className="mt-4">
            <DialogClose asChild>
              <Button variant="outline" disabled={mutation.isPending}>
                Cancel
              </Button>
            </DialogClose>
            <LoadingButton
              variant="destructive"
              type="submit"
              loading={mutation.isPending}
            >
              Delete
            </LoadingButton>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}

export default DeleteEpisode
