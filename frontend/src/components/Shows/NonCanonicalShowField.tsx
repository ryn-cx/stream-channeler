// TODO: Validate
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { useState } from "react"

import { ShowsService } from "@/client"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"

interface NonCanonicalShowFieldProps {
  showId: string
}

// TODO: Validate
export function NonCanonicalShowField({ showId }: NonCanonicalShowFieldProps) {
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const queryClient = useQueryClient()
  const [urlDraft, setUrlDraft] = useState("")

  const mutation = useMutation({
    mutationFn: () =>
      ShowsService.adminImportNonCanonicalShow({
        showId,
        requestBody: { url: urlDraft.trim() },
      }),
    onSuccess: () => {
      showSuccessToast("URL imported and linked to this show")
      setUrlDraft("")
      queryClient.invalidateQueries({ queryKey: ["shows"] })
      queryClient.invalidateQueries({ queryKey: ["episodes"] })
      queryClient.invalidateQueries({ queryKey: ["show-information", showId] })
      queryClient.invalidateQueries({ queryKey: ["canonical-show"] })
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
      <Label htmlFor="non-canonical-show-url">Link another show</Label>
      <div className="flex flex-wrap items-center gap-2">
        <Input
          id="non-canonical-show-url"
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
          Import as linked show
        </Button>
      </div>
      <p className="text-sm text-muted-foreground">
        Imports the address with whichever plugin handles it and links what it
        writes to this title as a non-canonical show.
      </p>
    </div>
  )
}
