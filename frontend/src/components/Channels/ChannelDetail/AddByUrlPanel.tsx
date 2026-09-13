// TODO: Validate
import { useMutation, useQuery } from "@tanstack/react-query"
import { Plus } from "lucide-react"
import { useState } from "react"
import Markdown from "react-markdown"
import { remarkAlert } from "remark-github-blockquote-alert"
import "remark-github-blockquote-alert/alert.css"
import { ChannelsService, PluginsService } from "@/client"
import { SourceOptionLabel } from "@/components/Common/SourceOptionLabel"
import { Button } from "@/components/ui/button"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"

// TODO: Validate
/**
 * Queue a list of addresses for import, one per line.
 *
 * A site can be picked to read its own URL formats, since what counts as an
 * address for a title is the site's own business and there is no guessing it from
 * the box. Nothing is imported here: the addresses go on the channel's queue and
 * are read from there.
 */
export function AddByUrlPanel({ channelId }: { channelId: string }) {
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const [urlsInput, setUrlsInput] = useState("")
  const [selectedPlugin, setSelectedPlugin] = useState<string | null>(null)

  const { data: urlImportPlugins } = useQuery({
    queryKey: ["url-import-plugins"],
    queryFn: () => PluginsService.importUrlInformation(),
  })

  const addUrlsMutation = useMutation({
    mutationFn: async (urls: string[]) => {
      for (let start = 0; start < urls.length; start += 100) {
        await ChannelsService.createChannelQueueUrls({
          channelId,
          requestBody: urls.slice(start, start + 100),
        })
      }
    },
    onMutate: (urls) => {
      showSuccessToast(
        `${urls.length} URL${urls.length !== 1 ? "s" : ""} added to import queue`,
      )
      setUrlsInput("")
    },
    onSettled: (_data, _error, _urls, _onMutateResult, context) =>
      context.client.invalidateQueries({
        queryKey: ["channelQueue", channelId],
      }),
    onError: (error) =>
      handleError.call(
        showErrorToast,
        error as Parameters<typeof handleError>[0],
      ),
  })

  // TODO: Validate
  const handleSubmit = () => {
    const urls = urlsInput
      .split("\n")
      .map((url) => url.trim())
      .filter((url) => url.length > 0)

    if (urls.length === 0) {
      showErrorToast("Please enter at least one URL")
      return
    }

    addUrlsMutation.mutate(urls)
  }

  return (
    <div className="border rounded-lg p-4 space-y-3">
      <p className="text-sm text-muted-foreground">
        One address per line. Select a site to see supported URL formats:
      </p>
      <Select
        value={selectedPlugin ?? "__none__"}
        onValueChange={(value) =>
          setSelectedPlugin(value === "__none__" ? null : value)
        }
      >
        <SelectTrigger>
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="__none__">Choose a site...</SelectItem>
          {(urlImportPlugins ?? []).map((plugin) => (
            <SelectItem key={plugin.name} value={plugin.name}>
              <SourceOptionLabel
                name={plugin.name}
                faviconUrl={plugin.favicon_url}
              />
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      {selectedPlugin && (
        <div className="text-sm text-muted-foreground [&_code]:bg-muted [&_code]:px-1.5 [&_code]:py-0.5 [&_code]:rounded [&_code]:text-xs [&_.markdown-alert-title_svg]:hidden">
          <Markdown remarkPlugins={[[remarkAlert, { legacyTitle: true }]]}>
            {(urlImportPlugins ?? []).find((p) => p.name === selectedPlugin)
              ?.instructions ?? ""}
          </Markdown>
        </div>
      )}
      <textarea
        value={urlsInput}
        onChange={(e) => setUrlsInput(e.target.value)}
        placeholder={"https://example.com/title-1\nhttps://example.com/title-2"}
        rows={6}
        className="w-full rounded-md border border-input px-3 py-2 text-sm outline-none"
        disabled={addUrlsMutation.isPending}
      />
      <div className="flex justify-end">
        <Button
          onClick={handleSubmit}
          disabled={addUrlsMutation.isPending}
          size="sm"
        >
          <Plus className="h-4 w-4 mr-1" />
          {addUrlsMutation.isPending ? "Adding URLs..." : "Add URLs"}
        </Button>
      </div>
    </div>
  )
}
