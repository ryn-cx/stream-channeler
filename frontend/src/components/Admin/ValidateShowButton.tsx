// TODO: Validate
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { Check } from "lucide-react"

import { ShowsService } from "@/client"
import { Button } from "@/components/ui/button"
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"
import { UNVALIDATED_SHOWS_QUERY_KEY } from "./unvalidatedShowsQuery"

// TODO: Validate
export function ValidateShowButton({
  showId,
  showName,
}: {
  showId: string
  showName: string | null | undefined
}) {
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()

  const validateMutation = useMutation({
    mutationFn: () => ShowsService.adminValidateShow({ showId }),
    onSuccess: () => {
      showSuccessToast(`Validated ${showName ?? "the show"}`)
      queryClient.invalidateQueries({ queryKey: UNVALIDATED_SHOWS_QUERY_KEY })
      queryClient.invalidateQueries({ queryKey: ["shows"] })
    },
    onError: (error: unknown) =>
      handleError.call(
        showErrorToast,
        error as Parameters<typeof handleError>[0],
      ),
  })

  return (
    <Button
      variant="outline"
      size="sm"
      disabled={validateMutation.isPending}
      onClick={() => validateMutation.mutate()}
    >
      <Check className="h-4 w-4" />
      Validate
    </Button>
  )
}
