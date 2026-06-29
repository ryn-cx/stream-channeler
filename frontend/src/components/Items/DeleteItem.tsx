import { useMutation, useQueryClient } from "@tanstack/react-query"
import { Trash2 } from "lucide-react"

import type { ApiError } from "@/client"
import { ItemsService } from "@/client"
import { ConfirmDialog } from "@/components/Common/ConfirmDialog"
import { TooltipIconButton } from "@/components/Common/TooltipIconButton"
import type { ItemsPublicWithPending } from "@/components/Items/types"
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"

interface DeleteItemProps {
  id: string
}

const DeleteItem = ({ id }: DeleteItemProps) => {
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()

  const deleteItem = async (id: string) => {
    await ItemsService.deleteItem({ itemId: id })
  }

  const mutation = useMutation({
    mutationFn: deleteItem,
    // When mutate is called:
    onMutate: async (deletedId) => {
      // Cancel any outgoing refetches
      // (so they don't overwrite our optimistic update)
      await queryClient.cancelQueries({ queryKey: ["items"] })

      // Snapshot the previous value
      const previousItems = queryClient.getQueriesData<ItemsPublicWithPending>({
        queryKey: ["items"],
      })

      // Optimistically update to the new value
      queryClient.setQueriesData<ItemsPublicWithPending>(
        { queryKey: ["items"] },
        (old) =>
          old
            ? {
                ...old,
                data: old.data.filter((item) => item.id !== deletedId),
                count: old.count - 1,
              }
            : old,
      )

      // Return a result with the snapshotted value
      return { previousItems }
    },
    onSuccess: () => {
      showSuccessToast("The item was deleted successfully")
    },
    // If the mutation fails,
    // use the result returned from onMutate to roll back
    onError: (err, _deletedId, context) => {
      for (const [queryKey, data] of context?.previousItems ?? []) {
        queryClient.setQueryData(queryKey, data)
      }
      handleError.call(showErrorToast, err as ApiError)
    },
    // Always refetch after error or success:
    onSettled: () => queryClient.invalidateQueries({ queryKey: ["items"] }),
  })

  return (
    <ConfirmDialog
      trigger={
        <TooltipIconButton
          label="Delete Item"
          icon={<Trash2 />}
          className="text-destructive hover:text-destructive"
        />
      }
      title="Delete Item"
      description="This item will be permanently deleted. Are you sure? You will not be able to undo this action."
      onConfirm={() => mutation.mutate(id)}
      isLoading={mutation.isPending}
    />
  )
}

export default DeleteItem
