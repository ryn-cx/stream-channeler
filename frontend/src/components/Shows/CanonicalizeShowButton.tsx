// TODO: Validate
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { useState } from "react"

import { ShowsService } from "@/client"
import { ConfirmDialog } from "@/components/Common/ConfirmDialog"
import { Button } from "@/components/ui/button"
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"

interface CanonicalizeShowButtonProps {
  showId: string
  canonicalShowIds: string[]
}

// TODO: Validate
export function CanonicalizeShowButton({
  showId,
  canonicalShowIds,
}: CanonicalizeShowButtonProps) {
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const queryClient = useQueryClient()
  const [isConfirming, setIsConfirming] = useState(false)

  const mutation = useMutation({
    mutationFn: () => ShowsService.adminCanonicalizeShow({ showId }),
    onSuccess: () => {
      showSuccessToast("Show is now a canonical show")
      queryClient.invalidateQueries({ queryKey: ["shows"] })
      queryClient.invalidateQueries({ queryKey: ["show-information", showId] })
      queryClient.invalidateQueries({ queryKey: ["canonical-show"] })
      queryClient.invalidateQueries({ queryKey: ["canonical-shows"] })
      queryClient.invalidateQueries({ queryKey: ["channels"] })
    },
    onError: (error: unknown) =>
      handleError.call(
        showErrorToast,
        error as Parameters<typeof handleError>[0],
      ),
  })

  const isLinked = canonicalShowIds.length > 0

  return (
    <div className="space-y-2">
      <Button
        type="button"
        variant="outline"
        disabled={!isLinked || mutation.isPending}
        onClick={() => setIsConfirming(true)}
      >
        Canonicalize Show
      </Button>
      <p className="text-sm text-muted-foreground">
        {isLinked
          ? "Makes this show canonical and puts it on every channel the titles it stands for are on. Any title left over is yours to take off those channels."
          : "This show already is a canonical show."}
      </p>
      <ConfirmDialog
        open={isConfirming}
        onOpenChange={setIsConfirming}
        title="Canonicalize Show"
        description="This show stops standing for the titles it is linked to and becomes a canonical show of its own. Every channel those titles are on gets this show added to it, and taking the old titles off those channels is left to you."
        confirmLabel="Canonicalize"
        variant="default"
        onConfirm={() => mutation.mutate()}
      />
    </div>
  )
}
