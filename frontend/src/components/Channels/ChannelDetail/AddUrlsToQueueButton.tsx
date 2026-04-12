// TODO: Validate
import { useMutation, useQuery } from "@tanstack/react-query"
import { Info, Link2, Plus, Search, Trash2 } from "lucide-react"
import { useState } from "react"
import Markdown from "react-markdown"
import { remarkAlert } from "remark-github-blockquote-alert"
import "remark-github-blockquote-alert/alert.css"
import type { ChannelQueueOutput } from "@/client"
import { ChannelsService } from "@/client"
import { OpenAPI } from "@/client/core/OpenAPI"
import { request as apiRequest } from "@/client/core/request"
import { Badge } from "@/components/ui/badge"
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
import { DropdownMenuItem } from "@/components/ui/dropdown-menu"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"
import { ShowSearch } from "./Search"

interface AddUrlsToQueueButtonProps {
  channelId: string
  isOwner?: boolean
  variant?: "button" | "menu"
}

function getStatusBadgeVariant(status: string) {
  switch (status) {
    case "Imported":
      return "default" // green/primary
    case "Failed":
      return "destructive" // red
    case "Importing":
      return "secondary" // gray/blue
    default:
      return "outline" // outlined
  }
}

export function AddUrlsToQueueButton({
  channelId,
  variant = "button",
}: AddUrlsToQueueButtonProps) {
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const [isOpen, setIsOpen] = useState(false)
  const [mode, setMode] = useState<"search" | "url">("search")
  const [urlsInput, setUrlsInput] = useState("")
  const [selectedPlugin, setSelectedPlugin] = useState<string | null>(null)
  const [noteDialogOpen, setNoteDialogOpen] = useState(false)
  const [selectedNote, setSelectedNote] = useState<string | null>(null)

  const { data: urlImportPlugins } = useQuery({
    queryKey: ["url-import-plugins"],
    queryFn: () =>
      apiRequest<Array<{ name: string; instructions: string }>>(OpenAPI, {
        method: "GET",
        url: "/api/v1/plugins/import-url-information",
      }),
    enabled: isOpen,
  })

  const { data: queueData, isLoading: isLoadingQueue } = useQuery({
    queryKey: ["channelQueue", channelId],
    queryFn: () => ChannelsService.getChannelQueue({ channelId }),
  })

  const queueEntries = queueData ?? []

  const addUrlsMutation = useMutation({
    mutationFn: (urls: string[]) =>
      ChannelsService.createChannelQueueUrls({
        channelId,
        requestBody: urls,
      }),
    // When mutate is called:
    onMutate: async (urls, context) => {
      // Cancel any outgoing refetches
      // (so they don't overwrite our optimistic update)
      await context.client.cancelQueries({
        queryKey: ["channelQueue", channelId],
      })

      // Snapshot the previous value
      const previousQueue = context.client.getQueryData([
        "channelQueue",
        channelId,
      ])

      // Optimistically update to the new value
      context.client.setQueryData(
        ["channelQueue", channelId],
        (oldData: any) => [
          ...(oldData ?? []),
          ...urls.map((url, index) => ({
            id: `placeholder_${index}`,
            url,
            status: "Pending",
            note: null,
            created_at: new Date().toISOString(),
          })),
        ],
      )

      showSuccessToast(
        `${urls.length} URL${urls.length !== 1 ? "s" : ""} added to import queue`,
      )
      setUrlsInput("")

      // Return a result with the snapshotted value
      return { previousQueue }
    },
    // If the mutation fails,
    // use the result returned from onMutate to roll back
    onError: (error, _urls, onMutateResult, context) => {
      context.client.setQueryData(
        ["channelQueue", channelId],
        onMutateResult?.previousQueue,
      )
      handleError.call(showErrorToast, error as any)
    },
    // Always refetch after error or success:
    onSettled: (_data, _error, _variables, _onMutateResult, context) =>
      context.client.invalidateQueries({
        queryKey: ["channelQueue", channelId],
      }),
  })

  const deleteUrlMutation = useMutation({
    mutationFn: (urlId: string) =>
      ChannelsService.deleteChannelQueueUrl({
        channelId,
        urlId,
      }),
    // When mutate is called:
    onMutate: async (urlId, context) => {
      // Cancel any outgoing refetches
      // (so they don't overwrite our optimistic update)
      await context.client.cancelQueries({
        queryKey: ["channelQueue", channelId],
      })

      // Snapshot the previous value
      const previousQueue = context.client.getQueryData([
        "channelQueue",
        channelId,
      ])

      // Optimistically update to the new value
      context.client.setQueryData(["channelQueue", channelId], (oldData: any) =>
        oldData.filter((entry: ChannelQueueOutput) => entry.id !== urlId),
      )

      showSuccessToast("URL removed from queue")

      // Return a result with the snapshotted value
      return { previousQueue }
    },
    // If the mutation fails,
    // use the result returned from onMutate to roll back
    onError: (_error, _urlId, onMutateResult, context) => {
      context.client.setQueryData(
        ["channelQueue", channelId],
        onMutateResult?.previousQueue,
      )
      showErrorToast("Failed to remove URL from queue")
    },
    // Always refetch after error or success:
    onSettled: (_data, _error, _variables, _onMutateResult, context) =>
      context.client.invalidateQueries({
        queryKey: ["channelQueue", channelId],
      }),
  })

  const clearQueueMutation = useMutation({
    mutationFn: () =>
      ChannelsService.clearChannelCompletedQueue({
        channelId,
      }),
    // When mutate is called:
    onMutate: async (_variables, context) => {
      // Cancel any outgoing refetches
      // (so they don't overwrite our optimistic update)
      await context.client.cancelQueries({
        queryKey: ["channelQueue", channelId],
      })

      // Snapshot the previous value
      const previousQueue = context.client.getQueryData([
        "channelQueue",
        channelId,
      ])

      // Optimistically update to the new value
      context.client.setQueryData(["channelQueue", channelId], (oldData: any) =>
        oldData.filter(
          (entry: ChannelQueueOutput) =>
            entry.status !== "Imported" && entry.status !== "Failed",
        ),
      )

      showSuccessToast("Completed queue entries cleared")

      // Return a result with the snapshotted value
      return { previousQueue }
    },
    // If the mutation fails,
    // use the result returned from onMutate to roll back
    onError: (_error, _variables, onMutateResult, context) => {
      context.client.setQueryData(
        ["channelQueue", channelId],
        onMutateResult?.previousQueue,
      )
      showErrorToast("Failed to clear queue")
    },
    // Always refetch after error or success:
    onSettled: (_data, _error, _variables, _onMutateResult, context) =>
      context.client.invalidateQueries({
        queryKey: ["channelQueue", channelId],
      }),
  })

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

  const showNote = (note: string | null | undefined) => {
    setSelectedNote(note || null)
    setNoteDialogOpen(true)
  }

  return (
    <>
      <Dialog open={isOpen} onOpenChange={setIsOpen}>
        <DialogTrigger asChild>
          {variant === "menu" ? (
            <DropdownMenuItem
              onSelect={(e) => {
                e.preventDefault()
              }}
            >
              <Plus className="mr-2 size-4" />
              Add Shows
            </DropdownMenuItem>
          ) : (
            <Button className="mt-2 mb-4">
              <Plus className="mr-2" />
              Add Shows
            </Button>
          )}
        </DialogTrigger>
        {/* sm:max-w-4xl - Needs to be really wide for URLs */}
        {/* max-h-[85vh] flex - Make it scrollable when it is too tall */}
        {/* flex-col - Put everything in a column */}
        <DialogContent className="sm:max-w-5xl max-h-[85vh] flex flex-col">
          <DialogHeader className="px-8">
            <DialogTitle>Add Shows</DialogTitle>
            <DialogDescription>
              {mode === "search"
                ? "Search for shows and movies to add to your channel."
                : "Add URLs to your channel directly, one per line."}
            </DialogDescription>
            <div>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setMode(mode === "search" ? "url" : "search")}
              >
                {mode === "search" ? (
                  <>
                    <Link2 className="h-4 w-4 mr-1" /> Add Media By URL
                  </>
                ) : (
                  <>
                    <Search className="h-4 w-4 mr-1" /> Add Media By Searching
                  </>
                )}
              </Button>
            </div>
          </DialogHeader>

          <div className="overflow-y-auto flex-1 min-h-0 px-8 py-4">
            {mode === "search" ? (
              <ShowSearch channelId={channelId} />
            ) : (
              <div className="space-y-4">
                <div className="border rounded-lg p-4 space-y-3">
                  <p className="text-sm text-muted-foreground">
                    Select a site to see supported URL formats:
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
                          {plugin.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  {selectedPlugin && (
                    <div className="text-sm text-muted-foreground [&_code]:bg-muted [&_code]:px-1.5 [&_code]:py-0.5 [&_code]:rounded [&_code]:text-xs [&_.markdown-alert-title_svg]:hidden">
                      <Markdown
                        remarkPlugins={[[remarkAlert, { legacyTitle: true }]]}
                      >
                        {(urlImportPlugins ?? []).find(
                          (p) => p.name === selectedPlugin,
                        )?.instructions ?? ""}
                      </Markdown>
                    </div>
                  )}
                  <textarea
                    value={urlsInput}
                    onChange={(e) => setUrlsInput(e.target.value)}
                    placeholder={
                      "https://example.com/show-1\nhttps://example.com/show-2"
                    }
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
                      {addUrlsMutation.isPending
                        ? "Adding URLs..."
                        : "Add URLs"}
                    </Button>
                  </div>
                </div>
              </div>
            )}
          </div>

          <div className="overflow-y-auto px-8 py-4 space-y-4">
            <div className="flex justify-between">
              <h3>Queue ({queueEntries.length} items)</h3>
              <Button
                variant="outline"
                size="sm"
                onClick={() => clearQueueMutation.mutate()}
                disabled={
                  clearQueueMutation.isPending || queueEntries.length === 0
                }
              >
                {clearQueueMutation.isPending
                  ? "Clearing Completed Entries..."
                  : "Clear Completed Entries"}
              </Button>
            </div>

            {isLoadingQueue ? (
              <p className="text-sm text-muted-foreground">Loading queue...</p>
            ) : queueEntries.length === 0 ? (
              <p className="text-sm text-muted-foreground">No items in queue</p>
            ) : (
              <div className="border rounded-lg">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>URL</TableHead>
                      <TableHead className="w-[100px]">Status</TableHead>
                      <TableHead className="w-[100px] text-center">
                        Actions
                      </TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {queueEntries.map((entry: ChannelQueueOutput) => (
                      <TableRow key={entry.id}>
                        <TableCell className="truncate">{entry.url}</TableCell>
                        <TableCell>
                          <Badge variant={getStatusBadgeVariant(entry.status)}>
                            {entry.status}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center justify-center gap-1">
                            <Button
                              variant="ghost"
                              size="icon-sm"
                              onClick={() => showNote(entry.note)}
                              title="Show note"
                            >
                              <Info className="h-4 w-4" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="icon-sm"
                              onClick={() => deleteUrlMutation.mutate(entry.id)}
                              disabled={deleteUrlMutation.isPending}
                              title="Delete URL"
                            >
                              <Trash2 className="h-4 w-4" />
                            </Button>
                          </div>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            )}
          </div>

          <DialogFooter className="px-8">
            <Button
              variant="outline"
              onClick={() => setIsOpen(false)}
              disabled={addUrlsMutation.isPending}
            >
              Close
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={noteDialogOpen} onOpenChange={setNoteDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Queue Entry Note</DialogTitle>
          </DialogHeader>
          <div className="py-4">
            <p className="text-sm whitespace-pre-wrap">
              {selectedNote || "No note available"}
            </p>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setNoteDialogOpen(false)}>
              Close
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )
}
