// TODO: Validate
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { useState } from "react"

import { ShowsService } from "@/client"
import { ConfirmDialog } from "@/components/Common/ConfirmDialog"
import { Button } from "@/components/ui/button"
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"

interface ForceUpdateShowButtonProps {
  showId: string
}

// TODO: Validate
export function ForceUpdateShowButton({ showId }: ForceUpdateShowButtonProps) {
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const queryClient = useQueryClient()
  const [isConfirming, setIsConfirming] = useState(false)

  const mutation = useMutation({
    mutationFn: () => ShowsService.adminForceUpdateShow({ showId }),
    onSuccess: () => {
      showSuccessToast("Show imported again")
      queryClient.invalidateQueries({ queryKey: ["shows"] })
      queryClient.invalidateQueries({ queryKey: ["episodes"] })
      queryClient.invalidateQueries({ queryKey: ["show-information", showId] })
      queryClient.invalidateQueries({ queryKey: ["episode-information"] })
      queryClient.invalidateQueries({ queryKey: ["canonical-show"] })
      queryClient.invalidateQueries({ queryKey: ["channels"] })
    },
    onError: (error: unknown) =>
      handleError.call(
        showErrorToast,
        error as Parameters<typeof handleError>[0],
      ),
  })

  return (
    <>
      <Button
        type="button"
        variant="destructive"
        disabled={mutation.isPending}
        onClick={() => setIsConfirming(true)}
      >
        Force Update
      </Button>
      <ConfirmDialog
        open={isConfirming}
        onOpenChange={setIsConfirming}
        title="Force Update Show"
        description="The show is read from its website again from scratch, whatever it was last read at, and everything it holds is written out again."
        confirmLabel="Force Update"
        variant="destructive"
        onConfirm={() => mutation.mutate()}
      />
    </>
  )
}
