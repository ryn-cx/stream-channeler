// TODO: Validate
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { useState } from "react"

import { ShowsService } from "@/client"
import { ConfirmDialog } from "@/components/Common/ConfirmDialog"
import { Button } from "@/components/ui/button"
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"

interface RelinkShowButtonProps {
  showId: string
}

// TODO: Validate
export function RelinkShowButton({ showId }: RelinkShowButtonProps) {
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const queryClient = useQueryClient()
  const [isConfirming, setIsConfirming] = useState(false)

  const mutation = useMutation({
    mutationFn: () => ShowsService.adminRelinkShowEpisodes({ showId }),
    onSuccess: () => {
      showSuccessToast("Episodes relinked")
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
        Relink
      </Button>
      <ConfirmDialog
        open={isConfirming}
        onOpenChange={setIsConfirming}
        title="Relink Episodes"
        description="Every episode link that nobody confirmed by hand is deleted and worked out again from scratch. Episodes you locked, and the ones settled as not on TMDB, are left alone."
        confirmLabel="Relink"
        variant="destructive"
        onConfirm={() => mutation.mutate()}
      />
    </>
  )
}
