// TODO: Validate
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { useState } from "react"

import type { UnmatchedTitleOutput } from "@/client"
import { UnmatchedTitlesService } from "@/client"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"
import { UNMATCHED_TITLES_QUERY_KEY } from "./unmatchedTitlesQuery"

// TODO: Validate
export function UnmatchedTitleImportForm({
  unmatchedTitle,
}: {
  unmatchedTitle: UnmatchedTitleOutput
}) {
  const [url, setUrl] = useState("")
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const queryClient = useQueryClient()

  const importMutation = useMutation({
    mutationFn: () =>
      UnmatchedTitlesService.adminImportUnmatchedTitle({
        unmatchedTitleId: unmatchedTitle.id,
        requestBody: { url },
      }),
    onSuccess: () => {
      showSuccessToast(`Imported from ${unmatchedTitle.provider_name}`)
      setUrl("")
    },
    onError: (error: unknown) =>
      handleError.call(
        showErrorToast,
        error as Parameters<typeof handleError>[0],
      ),
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: UNMATCHED_TITLES_QUERY_KEY })
      queryClient.invalidateQueries({ queryKey: ["titles"] })
      queryClient.invalidateQueries({ queryKey: ["episodes"] })
    },
  })

  return (
    <form
      className="flex items-center gap-2"
      onSubmit={(event) => {
        event.preventDefault()
        if (url.trim()) {
          importMutation.mutate()
        }
      }}
    >
      <Input
        value={url}
        onChange={(event) => setUrl(event.target.value)}
        placeholder={`${unmatchedTitle.provider_name} URL`}
        className="h-8 w-64"
      />
      <Button
        type="submit"
        variant="outline"
        size="sm"
        disabled={!url.trim() || importMutation.isPending}
      >
        Import
      </Button>
    </form>
  )
}
