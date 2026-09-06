// TODO: Validate
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { useState } from "react"

import { TitlesService } from "@/client"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"

interface NonCanonicalTitleFieldProps {
  titleId: string
}

// TODO: Validate
export function NonCanonicalTitleField({
  titleId,
}: NonCanonicalTitleFieldProps) {
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const queryClient = useQueryClient()
  const [urlDraft, setUrlDraft] = useState("")

  const mutation = useMutation({
    mutationFn: () =>
      TitlesService.adminLinkNonCanonicalTitleByUrl({
        titleId,
        requestBody: { url: urlDraft.trim() },
      }),
    onSuccess: () => {
      showSuccessToast("URL imported and linked to this title")
      setUrlDraft("")
      queryClient.invalidateQueries({ queryKey: ["titles"] })
      queryClient.invalidateQueries({ queryKey: ["episodes"] })
      queryClient.invalidateQueries({
        queryKey: ["title-information", titleId],
      })
      queryClient.invalidateQueries({ queryKey: ["canonical-title"] })
      queryClient.invalidateQueries({ queryKey: ["channels"] })
    },
    onError: (error: unknown) =>
      handleError.call(
        showErrorToast,
        error as Parameters<typeof handleError>[0],
      ),
  })

  return (
    <div className="space-y-2">
      <Label htmlFor="non-canonical-title-url">Link another title</Label>
      <div className="flex flex-wrap items-center gap-2">
        <Input
          id="non-canonical-title-url"
          value={urlDraft}
          onChange={(event) => setUrlDraft(event.target.value)}
          onKeyDown={(event) => {
            if (event.key !== "Enter") return
            event.preventDefault()
            if (urlDraft.trim().length > 0) mutation.mutate()
          }}
          placeholder="Address of a page holding this title"
          className="min-w-48 flex-1"
        />
        <Button
          type="button"
          variant="outline"
          disabled={urlDraft.trim().length === 0 || mutation.isPending}
          onClick={() => mutation.mutate()}
        >
          Import as linked title
        </Button>
      </div>
      <p className="text-sm text-muted-foreground">
        Imports the address with whichever plugin handles it and links what it
        writes to this title as a non-canonical title.
      </p>
    </div>
  )
}
