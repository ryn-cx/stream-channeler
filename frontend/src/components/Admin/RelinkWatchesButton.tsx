// TODO: Validate
import { useMutation } from "@tanstack/react-query"
import { Link2, Loader2 } from "lucide-react"

import { WatchesService } from "@/client"
import { Button } from "@/components/ui/button"
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"

// TODO: Validate
/**
 * Point every watch left without an episode back at one.
 *
 * Deleting an episode leaves the watches of it behind with nothing to join
 * through, and they stay dormant until another link to that episode exists.
 * This finds the ones that now have somewhere to point, choosing between the
 * links to an episode by the watcher's own source order.
 */
export function RelinkWatchesButton() {
  const { showSuccessToast, showWarningToast, showErrorToast } =
    useCustomToast()

  const relinkMutation = useMutation({
    mutationFn: () => WatchesService.adminRelinkWatches(),
    onSuccess: (results) => {
      if (results.detached === 0) {
        showSuccessToast("Every watch already points at an episode.")
        return
      }
      if (results.relinked === 0) {
        showWarningToast(
          `${results.detached} watches have no episode, and none of them names one this library carries.`,
        )
        return
      }
      showSuccessToast(
        `Relinked ${results.relinked} of ${results.detached} watches without an episode.`,
      )
    },
    onError: (error: unknown) => {
      handleError.call(
        showErrorToast,
        error as Parameters<typeof handleError>[0],
      )
    },
  })

  return (
    <Button
      variant="outline"
      onClick={() => relinkMutation.mutate()}
      disabled={relinkMutation.isPending}
    >
      {relinkMutation.isPending ? (
        <Loader2 className="size-4 animate-spin" />
      ) : (
        <Link2 className="size-4" />
      )}
      Resync watches
    </Button>
  )
}
