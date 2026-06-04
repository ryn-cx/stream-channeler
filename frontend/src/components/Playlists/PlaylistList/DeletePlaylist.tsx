// TODO: Validate
import { useMutation } from "@tanstack/react-query"
import { Trash2 } from "lucide-react"
import { useState } from "react"

import { PlaylistsService } from "@/client"
import { ConfirmDialog } from "@/components/Common/ConfirmDialog"
import { TooltipIconButton } from "@/components/Common/TooltipIconButton"
import type { PlaylistTableData } from "@/components/Playlists/PlaylistList/columns"
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

  const mutation = useMutation({
    mutationFn: (playlistId: string) =>
      PlaylistsService.deletePlaylist({ playlistId }),
    // When mutate is called:
    onMutate: async (_playlistId, context) => {
      // Cancel any outgoing refetches
      // (so they don't overwrite our optimistic update)
      await context.client.cancelQueries({ queryKey: ["playlists"] })
      // Snapshot the previous value
      const previousPlaylists = context.client.getQueryData<
        Array<PlaylistTableData>
      >(["playlists"])
      // Optimistically update to the new value
      context.client.setQueryData<Array<PlaylistTableData>>(
        ["playlists"],
        (old) =>
          (old ?? []).map((p) => (p.id === id ? { ...p, pending: true } : p)),
      )
      // Return a result with the snapshotted value
      return { previousPlaylists }
    },
    onSuccess: (_data, _playlistId, _onMutateResult, context) => {
      showSuccessToast("The playlist was deleted successfully")
      onSuccess()
      context.client.setQueryData<Array<PlaylistTableData>>(
        ["playlists"],
        (old) => old?.filter((p) => p.id !== id),
      )
    },
    // If the mutation fails,
    // use the result returned from onMutate to roll back
    onError: (error, _playlistId, onMutateResult, context) => {
      context.client.setQueryData(
        ["playlists"],
        onMutateResult?.previousPlaylists,
      )
      handleError.call(showErrorToast, error as any)
    },
    // Always refetch after error or success:
    onSettled: (_data, _error, _variables, _onMutateResult, context) =>
      context.client.invalidateQueries({ queryKey: ["playlists"] }),
  })

  return (
    <>
      {externalOpen === undefined && (
        <TooltipIconButton
          label="Delete Playlist"
          icon={<Trash2 />}
          className="text-destructive hover:text-destructive"
          onClick={() => setIsOpen(true)}
        />
      )}
      <ConfirmDialog
        open={isOpen}
        onOpenChange={setIsOpen}
        title="Delete Playlist"
        description="This playlist will be permanently deleted. Are you sure? You will not be able to undo this action."
        confirmLabel="Delete"
        onConfirm={() => mutation.mutate(id)}
      />
    </>
  )
}

export default DeletePlaylist
