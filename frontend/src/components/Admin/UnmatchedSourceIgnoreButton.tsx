// TODO: Validate
import { useMutation, useQueryClient } from "@tanstack/react-query"

import type { UnmatchedSourceOutput } from "@/client"
import { UnmatchedSourcesService } from "@/client"
import { Button } from "@/components/ui/button"
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"
import { UNMATCHED_SOURCES_QUERY_KEY } from "./unmatchedSourcesQuery"

// TODO: Validate
export function UnmatchedSourceIgnoreButton({
  unmatchedSource,
}: {
  unmatchedSource: UnmatchedSourceOutput
}) {
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const queryClient = useQueryClient()

  const ignoreMutation = useMutation({
    mutationFn: () =>
      UnmatchedSourcesService.adminIgnoreUnmatchedSource({
        unmatchedSourceId: unmatchedSource.id,
      }),
    onSuccess: () =>
      showSuccessToast(`Ignoring ${unmatchedSource.provider_name}`),
    onError: (error: unknown) =>
      handleError.call(
        showErrorToast,
        error as Parameters<typeof handleError>[0],
      ),
    onSettled: () =>
      queryClient.invalidateQueries({ queryKey: UNMATCHED_SOURCES_QUERY_KEY }),
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
