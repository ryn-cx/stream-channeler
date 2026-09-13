// TODO: Validate
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { useState } from "react"

import type { MissingSourceTitleOutput } from "@/client"
import { TitlesService } from "@/client"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"
import { TITLES_MISSING_SOURCES_QUERY_KEY } from "./titlesMissingSourcesQuery"

// TODO: Validate
export function LinkTitleImportForm({
  title,
}: {
  title: MissingSourceTitleOutput
}) {
  const [url, setUrl] = useState("")
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const queryClient = useQueryClient()

  const importMutation = useMutation({
    mutationFn: () =>
      TitlesService.adminLinkLinkedTitleByUrl({
        titleId: title.id,
        requestBody: { url: url.trim() },
      }),
    onSuccess: () => {
      showSuccessToast(`Linked a source to ${title.name ?? title.key}`)
      setUrl("")
    },
    onError: (error: unknown) =>
      handleError.call(
        showErrorToast,
        error as Parameters<typeof handleError>[0],
      ),
    onSettled: () => {
      queryClient.invalidateQueries({
        queryKey: TITLES_MISSING_SOURCES_QUERY_KEY,
      })
      queryClient.invalidateQueries({ queryKey: ["titles"] })
      queryClient.invalidateQueries({ queryKey: ["episodes"] })
      queryClient.invalidateQueries({ queryKey: ["tmdb-title"] })
      queryClient.invalidateQueries({ queryKey: ["channels"] })
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
        placeholder="Address of a page holding this title"
        className="h-8 w-64"
      />
      <Button
        type="submit"
        variant="outline"
        size="sm"
        disabled={!url.trim() || importMutation.isPending}
      >
        Link
      </Button>
    </form>
  )
}
