// TODO: Validate
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { useState } from "react"

import type { UnmatchedSourceOutput } from "@/client"
import { UnmatchedSourcesService } from "@/client"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"
import { UNMATCHED_SOURCES_QUERY_KEY } from "./unmatchedSourcesQuery"

// TODO: Validate
export function UnmatchedSourceImportForm({
  unmatchedSource,
}: {
  unmatchedSource: UnmatchedSourceOutput
}) {
  const [url, setUrl] = useState("")
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const queryClient = useQueryClient()

  const importMutation = useMutation({
    mutationFn: () =>
      UnmatchedSourcesService.adminImportUnmatchedSource({
        unmatchedSourceId: unmatchedSource.id,
        requestBody: { url },
      }),
    onSuccess: () => {
      showSuccessToast(`Imported from ${unmatchedSource.provider_name}`)
      setUrl("")
    },
    onError: (error: unknown) =>
      handleError.call(
        showErrorToast,
        error as Parameters<typeof handleError>[0],
      ),
    onSettled: () =>
      queryClient.invalidateQueries({ queryKey: UNMATCHED_SOURCES_QUERY_KEY }),
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
        placeholder={`${unmatchedSource.provider_name} URL`}
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
