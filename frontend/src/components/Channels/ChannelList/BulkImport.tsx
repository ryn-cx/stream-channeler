// TODO: Validate
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { FileUp } from "lucide-react"
import { useState } from "react"
import { ChannelsService } from "@/client"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"

const PLACEHOLDER = `{
  "channel-id-here": [
    "https://example.com/show-1",
    "https://example.com/show-2"
  ],
  "another-channel-id": [
    "https://example.com/show-3"
  ]
}`

export function BulkImport() {
  const [isOpen, setIsOpen] = useState(false)
  const [jsonInput, setJsonInput] = useState("")
  const [parseError, setParseError] = useState<string | null>(null)
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const queryClient = useQueryClient()

  const mutation = useMutation({
    mutationFn: (payload: Record<string, string[]>) =>
      ChannelsService.bulkImportQueueUrls({ requestBody: payload }),
    onSuccess: (data: any) => {
      showSuccessToast(data?.message ?? "URLs imported successfully")
      queryClient.invalidateQueries({ queryKey: ["channelQueue"] })
      setJsonInput("")
      setParseError(null)
      setIsOpen(false)
    },
    onError: handleError.bind(showErrorToast),
  })

  const handleSubmit = () => {
    try {
      const parsed = JSON.parse(jsonInput)

      if (
        typeof parsed !== "object" ||
        parsed === null ||
        Array.isArray(parsed)
      ) {
        setParseError(
          "Input must be a JSON object mapping channel IDs to URL arrays",
        )
        return
      }

      for (const [channelId, urls] of Object.entries(parsed)) {
        if (!channelId) {
          setParseError("Channel ID keys must not be empty")
          return
        }
        if (
          !Array.isArray(urls) ||
          (urls as unknown[]).some((url) => typeof url !== "string")
        ) {
          setParseError(`Value for "${channelId}" must be an array of strings`)
          return
        }
      }

      setParseError(null)
      mutation.mutate(parsed)
    } catch {
      setParseError("Invalid JSON")
    }
  }

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      <DialogTrigger asChild>
        <Button>
          <FileUp className="mr-2" />
          Bulk Import
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-3xl max-h-[85vh] flex flex-col">
        <DialogHeader>
          <DialogTitle>Bulk Import</DialogTitle>
          <DialogDescription>
            Paste a JSON array to add URLs to multiple channels at once.
          </DialogDescription>
        </DialogHeader>

        <div className="overflow-y-auto py-4 flex-1 min-h-0 space-y-2">
          <textarea
            value={jsonInput}
            onChange={(event) => {
              setJsonInput(event.target.value)
              setParseError(null)
            }}
            placeholder={PLACEHOLDER}
            rows={14}
            className="w-full rounded-md border border-input px-3 py-2 text-sm font-mono outline-none"
          />
          {parseError && (
            <p className="text-sm text-destructive">{parseError}</p>
          )}
        </div>

        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => setIsOpen(false)}
            disabled={mutation.isPending}
          >
            Cancel
          </Button>
          <Button
            onClick={handleSubmit}
            disabled={mutation.isPending || !jsonInput.trim()}
          >
            {mutation.isPending ? "Importing..." : "Import All"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
