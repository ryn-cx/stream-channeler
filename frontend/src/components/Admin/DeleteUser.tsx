import { useMutation, useQueryClient } from "@tanstack/react-query"
import { Trash2 } from "lucide-react"

import type { ApiError } from "@/client"
import { UsersService } from "@/client"
import type { UsersPublicWithPending } from "@/components/Admin/types"
import { ConfirmDialog } from "@/components/Common/ConfirmDialog"
import { TooltipIconButton } from "@/components/Common/TooltipIconButton"
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"

interface DeleteUserProps {
  id: string
}

const DeleteUser = ({ id }: DeleteUserProps) => {
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()

  const deleteUser = async (id: string) => {
    await UsersService.deleteUser({ userId: id })
  }

  const mutation = useMutation({
    mutationFn: deleteUser,
    // When mutate is called:
    onMutate: async (deletedId) => {
      // Cancel any outgoing refetches
      // (so they don't overwrite our optimistic update)
      await queryClient.cancelQueries({ queryKey: ["users"] })

      // Snapshot the previous value
      const previousUsers = queryClient.getQueriesData<UsersPublicWithPending>({
        queryKey: ["users"],
      })

      // Optimistically update to the new value
      queryClient.setQueriesData<UsersPublicWithPending>(
        { queryKey: ["users"] },
        (old) =>
          old
            ? {
                ...old,
                data: old.data.filter((user) => user.id !== deletedId),
                count: old.count - 1,
              }
            : old,
      )

      // Return a result with the snapshotted value
      return { previousUsers }
    },
    onSuccess: () => {
      showSuccessToast("The user was deleted successfully")
    },
    // If the mutation fails,
    // use the result returned from onMutate to roll back
    onError: (err, _deletedId, context) => {
      for (const [queryKey, data] of context?.previousUsers ?? []) {
        queryClient.setQueryData(queryKey, data)
      }
      handleError.call(showErrorToast, err as ApiError)
    },
    // Always refetch after error or success:
    onSettled: () => queryClient.invalidateQueries({ queryKey: ["users"] }),
  })

  return (
    <ConfirmDialog
      trigger={
        <TooltipIconButton
          label="Delete User"
          icon={<Trash2 />}
          className="text-destructive hover:text-destructive"
        />
      }
      title="Delete User"
      description={
        <>
          All items associated with this user will also be{" "}
          <strong>permanently deleted.</strong> Are you sure? You will not be
          able to undo this action.
        </>
      }
      onConfirm={() => mutation.mutate(id)}
      isLoading={mutation.isPending}
    />
  )
}

export default DeleteUser
