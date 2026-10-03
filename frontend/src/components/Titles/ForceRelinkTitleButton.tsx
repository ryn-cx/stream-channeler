// TODO: Validate
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { useState } from "react"

import { TitlesService } from "@/client"
import { ConfirmDialog } from "@/components/Common/ConfirmDialog"
import { Button } from "@/components/ui/button"
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"

interface ForceRelinkTitleButtonProps {
  titleId: string
}

// TODO: Validate
export function ForceRelinkTitleButton({
  titleId,
}: ForceRelinkTitleButtonProps) {
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const queryClient = useQueryClient()
  const [isConfirming, setIsConfirming] = useState(false)

  const mutation = useMutation({
    mutationFn: () => TitlesService.adminRelinkTitleEpisodes({ titleId }),
    onSuccess: () => {
      showSuccessToast("Title linked again")
      queryClient.invalidateQueries({ queryKey: ["titles"] })
      queryClient.invalidateQueries({ queryKey: ["episodes"] })
      queryClient.invalidateQueries({
        queryKey: ["title-information", titleId],
      })
      queryClient.invalidateQueries({ queryKey: ["episode-information"] })
      queryClient.invalidateQueries({ queryKey: ["tmdb-title"] })
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
        Force Relink
      </Button>
      <ConfirmDialog
        open={isConfirming}
        onOpenChange={setIsConfirming}
        title="Force Relink Title"
        description="Every automatically matched episode link on the title is worked out again from scratch. Links set by hand are left where they are."
        confirmLabel="Force Relink"
        variant="destructive"
        onConfirm={() => mutation.mutate()}
      />
    </>
  )
}
