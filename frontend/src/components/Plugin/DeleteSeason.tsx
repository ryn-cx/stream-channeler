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

import type { SeasonTableData } from "./seasonColumns"

type SeasonsData = Array<SeasonTableData>

interface DeleteSeasonProps {
  season: SeasonTableData
}

const DeleteSeason = ({ season }: DeleteSeasonProps) => {
  const { showKey } = useParams({ strict: false })
  const [isOpen, setIsOpen] = useState(false)
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const { handleSubmit } = useForm()
  const queryKey = ["shows", showKey, "seasons"]

  const mutation = useMutation({
    mutationFn: (seasonId: string) =>
      request(OpenAPI, {
        method: "DELETE",
        url: "/api/v1/seasons/{season_id}",
        path: { season_id: seasonId },
      }),
    onMutate: async (_seasonKey, context) => {
      await context.client.cancelQueries({ queryKey })
      const previous = context.client.getQueryData<SeasonsData>(queryKey)

      context.client.setQueryData<SeasonsData>(queryKey, (old) =>
        old!.filter((s) => s.key !== season.key),
      )

      return { previous }
    },
    onSuccess: () => {
      showSuccessToast("Season deleted successfully")
      setIsOpen(false)
    },
    onError: (error, _seasonKey, onMutateResult, context) => {
      context.client.setQueryData(queryKey, onMutateResult?.previous)
      handleError.call(showErrorToast, error as any)
    },
    onSettled: (_data, _error, _variables, _onMutateResult, context) =>
      context.client.invalidateQueries({ queryKey }),
  })

  const onSubmit = () => {
    mutation.mutate(season.id)
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
          <p>Delete season</p>
        </TooltipContent>
      </Tooltip>
      <DialogContent className="sm:max-w-md">
        <form onSubmit={handleSubmit(onSubmit)}>
          <DialogHeader>
            <DialogTitle>Delete Season</DialogTitle>
            <DialogDescription>
              All data associated with this season will be{" "}
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

export default DeleteSeason
