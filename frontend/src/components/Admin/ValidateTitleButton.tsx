// TODO: Validate
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { Check } from "lucide-react"

import { TitlesService } from "@/client"
import { Button } from "@/components/ui/button"
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"
import { UNVALIDATED_TITLES_QUERY_KEY } from "./unvalidatedTitlesQuery"

// TODO: Validate
export function ValidateTitleButton({
  titleId,
  titleName,
}: {
  titleId: string
  titleName: string | null | undefined
}) {
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()

  const validateMutation = useMutation({
    mutationFn: () => TitlesService.adminValidateTitle({ titleId }),
    onSuccess: () => {
      showSuccessToast(`Validated ${titleName ?? "the title"}`)
      queryClient.invalidateQueries({ queryKey: UNVALIDATED_TITLES_QUERY_KEY })
      queryClient.invalidateQueries({ queryKey: ["titles"] })
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
