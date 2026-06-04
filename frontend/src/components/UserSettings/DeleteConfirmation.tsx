// TODO: Validate
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { useState } from "react"

import { UsersService } from "@/client"
import { ConfirmDialog } from "@/components/Common/ConfirmDialog"
import { Button } from "@/components/ui/button"
import useAuth from "@/hooks/useAuth"
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"

const DeleteConfirmation = () => {
  const [isOpen, setIsOpen] = useState(false)
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const { logout } = useAuth()

  const mutation = useMutation({
    mutationFn: () => UsersService.deleteUserMe(),
    onSuccess: () => {
      showSuccessToast("Your account has been successfully deleted")
      logout()
    },
    onError: handleError.bind(showErrorToast),
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["currentUser"] })
    },
  })

  return (
    <>
      <Button
        variant="destructive"
        className="mt-3"
        onClick={() => setIsOpen(true)}
      >
        Delete Account
      </Button>
      <ConfirmDialog
        open={isOpen}
        onOpenChange={setIsOpen}
        title="Confirmation Required"
        description={
          <>
            All your account data will be <strong>permanently deleted.</strong>{" "}
            If you are sure, please click <strong>"Confirm"</strong> to proceed.
            This action cannot be undone.
          </>
        }
        confirmLabel="Delete"
        onConfirm={() => mutation.mutate()}
      />
    </>
  )
}

export default DeleteConfirmation
