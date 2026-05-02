// TODO: Validate
import { useMutation } from "@tanstack/react-query"
import { useState } from "react"

import { type UserPublic, type UsersPublic, UsersService } from "@/client"
import { DeleteConfirmContent } from "@/components/Common/DeleteConfirmContent"
import { DeleteIconTrigger } from "@/components/Common/DeleteIconTrigger"
import { Dialog } from "@/components/ui/dialog"
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"

interface DeleteUserProps {
  user: UserPublic
}

const DeleteUser = ({ user }: DeleteUserProps) => {
  const [isOpen, setIsOpen] = useState(false)
  const { showSuccessToast, showErrorToast } = useCustomToast()

  const mutation = useMutation({
    mutationFn: (id: string) => UsersService.deleteUser({ userId: id }),
    // When mutate is called:
    onMutate: async (_userId, context) => {
      // Cancel any outgoing refetches
      // (so they don't overwrite our optimistic update)
      await context.client.cancelQueries({ queryKey: ["users"] })

      // Snapshot the previous value
      const previousUsers = context.client.getQueryData<UsersPublic>(["users"])

      // Optimistically update to the new value
      context.client.setQueryData<UsersPublic>(["users"], (old) => ({
        ...old!,
        data: old!.data.filter((u) => u.id !== user.id),
      }))

      // Return a result with the snapshotted value
      return { previousUsers }
    },
    onSuccess: () => {
      showSuccessToast("The user was deleted successfully")
      setIsOpen(false)
    },
    // If the mutation fails,
    // use the result returned from onMutate to roll back
    onError: (error, _userId, onMutateResult, context) => {
      context.client.setQueryData(["users"], onMutateResult?.previousUsers)
      handleError.call(showErrorToast, error as any)
    },
    // Always refetch after error or success:
    onSettled: (_data, _error, _variables, _onMutateResult, context) =>
      context.client.invalidateQueries({ queryKey: ["users"] }),
  })

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      <DeleteIconTrigger tooltip="Delete user" />
      <DeleteConfirmContent
        title="Delete User"
        description={
          <>
            All items associated with this user will also be{" "}
            <strong>permanently deleted.</strong> Are you sure? You will not be
            able to undo this action.
          </>
        }
        isPending={mutation.isPending}
        onSubmit={() => mutation.mutate(user.id)}
      />
    </Dialog>
  )
}

export default DeleteUser
