// TODO: Validate
import { useMutation, useQueryClient } from "@tanstack/react-query"

import type { UnmatchedTitleOutput } from "@/client"
import { UnmatchedTitlesService } from "@/client"
import { Button } from "@/components/ui/button"
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"
import { UNMATCHED_TITLES_QUERY_KEY } from "./unmatchedTitlesQuery"

// TODO: Validate
export function UnmatchedTitleIgnoreButton({
  unmatchedTitle,
}: {
  unmatchedTitle: UnmatchedTitleOutput
}) {
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const queryClient = useQueryClient()

  const ignoreMutation = useMutation({
    mutationFn: () =>
      UnmatchedTitlesService.adminIgnoreUnmatchedTitle({
        unmatchedTitleId: unmatchedTitle.id,
      }),
    onSuccess: () =>
      showSuccessToast(`Ignoring ${unmatchedTitle.provider_name}`),
    onError: (error: unknown) =>
      handleError.call(
        showErrorToast,
        error as Parameters<typeof handleError>[0],
      ),
    onSettled: () =>
      queryClient.invalidateQueries({ queryKey: UNMATCHED_TITLES_QUERY_KEY }),
  })

  return (
    <Button
      type="button"
      variant="outline"
      size="sm"
      disabled={ignoreMutation.isPending}
      onClick={() => ignoreMutation.mutate()}
    >
      Ignore
    </Button>
  )
}
