// TODO: Validate
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { useState } from "react"

import { TitlesService } from "@/client"
import { ConfirmDialog } from "@/components/Common/ConfirmDialog"
import { Button } from "@/components/ui/button"
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"

interface UnlinkTitleButtonProps {
  titleId: string
  tmdbTitleIds: string[]
}

// TODO: Validate
export function UnlinkTitleButton({
  titleId,
  tmdbTitleIds,
}: UnlinkTitleButtonProps) {
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const queryClient = useQueryClient()
  const [isConfirming, setIsConfirming] = useState(false)

  const mutation = useMutation({
    mutationFn: () => TitlesService.adminUnlinkTitle({ titleId }),
    onSuccess: () => {
      showSuccessToast("Title is now a tmdb title")
      queryClient.invalidateQueries({ queryKey: ["titles"] })
      queryClient.invalidateQueries({
        queryKey: ["title-information", titleId],
      })
      queryClient.invalidateQueries({ queryKey: ["tmdb-title"] })
      queryClient.invalidateQueries({ queryKey: ["tmdb-titles"] })
      queryClient.invalidateQueries({ queryKey: ["channels"] })
    },
    onError: (error: unknown) =>
      handleError.call(
        showErrorToast,
        error as Parameters<typeof handleError>[0],
      ),
  })

  const isLinked = tmdbTitleIds.length > 0

  return (
    <div className="space-y-2">
      <Button
        type="button"
        variant="outline"
        disabled={!isLinked || mutation.isPending}
        onClick={() => setIsConfirming(true)}
      >
        Tmdbize Title
      </Button>
      <p className="text-sm text-muted-foreground">
        {isLinked
          ? "Makes this title tmdb and puts it on every channel the titles it stands for are on. Any title left over is yours to take off those channels."
          : "This title already is a tmdb title."}
      </p>
      <ConfirmDialog
        open={isConfirming}
        onOpenChange={setIsConfirming}
        title="Tmdbize Title"
        description="This title stops standing for the titles it is linked to and becomes a tmdb title of its own. Every channel those titles are on gets this title added to it, and taking the old titles off those channels is left to you."
        confirmLabel="Tmdbize"
        variant="default"
        onConfirm={() => mutation.mutate()}
      />
    </div>
  )
}
