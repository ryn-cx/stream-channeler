// TODO: Validate
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { useState } from "react"

import { TitlesService } from "@/client"
import { ConfirmDialog } from "@/components/Common/ConfirmDialog"
import { Button } from "@/components/ui/button"
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"

interface ForceUpdateTitleButtonProps {
  titleId: string
}

// TODO: Validate
export function ForceUpdateTitleButton({
  titleId,
}: ForceUpdateTitleButtonProps) {
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const queryClient = useQueryClient()
  const [isConfirming, setIsConfirming] = useState(false)

  const mutation = useMutation({
    mutationFn: () => TitlesService.adminForceUpdateTitle({ titleId }),
    onSuccess: () => {
      showSuccessToast("Title imported again")
      queryClient.invalidateQueries({ queryKey: ["titles"] })
      queryClient.invalidateQueries({ queryKey: ["episodes"] })
      queryClient.invalidateQueries({
        queryKey: ["title-information", titleId],
      })
      queryClient.invalidateQueries({ queryKey: ["episode-information"] })
      queryClient.invalidateQueries({ queryKey: ["canonical-title"] })
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
        title="Force Update Title"
        description="The title is read from its website again from scratch, whatever it was last read at, and everything it holds is written out again."
        confirmLabel="Force Update"
        variant="destructive"
        onConfirm={() => mutation.mutate()}
      />
    </>
  )
}
