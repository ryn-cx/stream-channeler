// TODO: Validate
import { useMutation } from "@tanstack/react-query"
import { Trash2 } from "lucide-react"
import { useState } from "react"
import { useForm } from "react-hook-form"

import { type PlaylistOutput, PlaylistsService } from "@/client"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { LoadingButton } from "@/components/ui/loading-button"
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"

interface DeletePlaylistProps {
  id: string
  onSuccess?: () => void
  externalOpen?: boolean
  onExternalClose?: () => void
}

const DeletePlaylist = ({
  id,
  onSuccess = () => {},
  externalOpen,
  onExternalClose,
}: DeletePlaylistProps) => {
  const [internalOpen, setInternalOpen] = useState(false)
  const isOpen = externalOpen ?? internalOpen
  const setIsOpen = (open: boolean) => {
    if (externalOpen !== undefined) {
      if (!open) onExternalClose?.()
    } else {
      setInternalOpen(open)
    }
  }
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const { handleSubmit } = useForm()

  const mutation = useMutation({
    mutationFn: (playlistId: string) =>
      PlaylistsService.deletePlaylist({ playlistId }),
    onMutate: async (_playlistId, context) => {
      await context.client.cancelQueries({ queryKey: ["playlists"] })
      const previousPlaylists = context.client.getQueryData<
        Array<PlaylistOutput>
      >(["playlists"])
      context.client.setQueryData<Array<PlaylistOutput>>(["playlists"], (old) =>
        (old ?? []).filter((p) => p.id !== id),
      )
      return { previousPlaylists }
    },
    onSuccess: () => {
      showSuccessToast("The playlist was deleted successfully")
      setIsOpen(false)
      onSuccess()
    },
    onError: (error, _playlistId, onMutateResult, context) => {
      context.client.setQueryData(
        ["playlists"],
        onMutateResult?.previousPlaylists,
      )
      handleError.call(showErrorToast, error as any)
    },
    onSettled: (_data, _error, _variables, _onMutateResult, context) =>
      context.client.invalidateQueries({ queryKey: ["playlists"] }),
  })

  const onSubmit = async () => {
    mutation.mutate(id)
  }

  return (
    <>
      {externalOpen === undefined && (
        <Button
          variant="ghost"
          size="icon"
          title="Delete playlist"
          onClick={() => setIsOpen(true)}
        >
          <Trash2 className="size-4 text-destructive" />
        </Button>
      )}
      {isOpen && (
        <Dialog open={isOpen} onOpenChange={setIsOpen}>
          <DialogContent className="sm:max-w-md">
            <form onSubmit={handleSubmit(onSubmit)}>
              <DialogHeader>
                <DialogTitle>Delete Playlist</DialogTitle>
                <DialogDescription>
                  This playlist will be permanently deleted. Are you sure? You
                  will not be able to undo this action.
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
      )}
    </>
  )
}

export default DeletePlaylist
