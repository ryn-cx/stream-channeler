// TODO: Validate
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { CircleSlash } from "lucide-react"

import { TitlesService } from "@/client"
import { UNVALIDATED_TITLES_QUERY_KEY } from "@/components/Admin/unvalidatedTitlesQuery"
import { Button } from "@/components/ui/button"
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"

// TODO: Validate
export function MarkTitleAbsentButton({
  titleId,
  titleName,
}: {
  titleId: string
  titleName: string | null | undefined
}) {
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()

  const absentMutation = useMutation({
    mutationFn: () => TitlesService.adminMarkTitleAbsentFromTmdb({ titleId }),
    onSuccess: () => {
      showSuccessToast(`Marked ${titleName ?? "the title"} as not on TMDB`)
      queryClient.invalidateQueries({ queryKey: UNVALIDATED_TITLES_QUERY_KEY })
      queryClient.invalidateQueries({ queryKey: ["titles"] })
      queryClient.invalidateQueries({
        queryKey: ["title-information", titleId],
      })
      queryClient.invalidateQueries({ queryKey: ["tmdb-title"] })
      queryClient.invalidateQueries({ queryKey: ["tmdb-titles"] })
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
      disabled={absentMutation.isPending}
      title="Settle this as a title TMDB has no record of"
      onClick={() => absentMutation.mutate()}
    >
      <CircleSlash className="h-4 w-4" />
      Not on TMDB
    </Button>
  )
}
