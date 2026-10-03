// TODO: Validate
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { Check, Unlink } from "lucide-react"

import type { MismatchedTitleOutput } from "@/client"
import { TitlesService } from "@/client"
import { Button } from "@/components/ui/button"
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"
import { TITLE_LINK_HISTORY_QUERY_KEY } from "./titleLinkHistoryQuery"

// TODO: Validate
export function MismatchedTitleActions({
  entry,
}: {
  entry: MismatchedTitleOutput
}) {
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const queryClient = useQueryClient()

  const onError = (error: unknown) =>
    handleError.call(showErrorToast, error as Parameters<typeof handleError>[0])
  const onSettled = () => {
    queryClient.invalidateQueries({ queryKey: ["titles"] })
    queryClient.invalidateQueries({ queryKey: TITLE_LINK_HISTORY_QUERY_KEY })
  }

  const verifyMutation = useMutation({
    mutationFn: () =>
      TitlesService.adminValidateTitle({ titleId: entry.title_id }),
    onSuccess: () => showSuccessToast("Title link verified"),
    onError,
    onSettled,
  })

  const unlinkMutation = useMutation({
    mutationFn: () =>
      TitlesService.adminUnlinkTitleFromTmdb({
        titleId: entry.title_id,
        tmdbTitleId: entry.tmdb_title_id,
      }),
    onSuccess: () => showSuccessToast("Title unlinked"),
    onError,
    onSettled,
  })

  const pending = verifyMutation.isPending || unlinkMutation.isPending

  return (
    <span className="flex items-center gap-2">
      <Button
        type="button"
        variant="outline"
        size="sm"
        disabled={pending}
        onClick={() => verifyMutation.mutate()}
      >
        <Check />
        Verify
      </Button>
      <Button
        type="button"
        variant="destructive"
        size="sm"
        disabled={pending}
        onClick={() => unlinkMutation.mutate()}
      >
        <Unlink />
        Unlink
      </Button>
    </span>
  )
}
