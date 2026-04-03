// TODO: Validate
import { useMutation, useQuery } from "@tanstack/react-query"
import { Info, Plus, Trash2 } from "lucide-react"
import { useState } from "react"
import type { ChannelQueueOutput } from "@/client"
import { ChannelsService } from "@/client"
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
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"
import { JustWatchSearch } from "./JustWatchSearch"

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
  const [urlsInput, setUrlsInput] = useState("")
  const [noteDialogOpen, setNoteDialogOpen] = useState(false)
  const [selectedNote, setSelectedNote] = useState<string | null>(null)

  const { data: queueData, isLoading: isLoadingQueue } = useQuery({
    queryKey: ["channelQueue", channelId],
    queryFn: () => ChannelsService.getUserChannelQueue({ channelId }),
  })

  const queueEntries = queueData?.data || []

  const addUrlsMutation = useMutation({
    mutationFn: (urls: string[]) =>
      ChannelsService.createUserChannelQueueUrls({
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
        (oldData: any) => ({
          ...oldData,
          data: [
            ...oldData.data,
            ...urls.map((url, index) => ({
              id: `placeholder_${index}`,
              url,
              status: "Pending",
              note: null,
              created_at: new Date().toISOString(),
            })),
          ],
        }),
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
      ChannelsService.deleteUserChannelQueueUrl({
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
      context.client.setQueryData(
        ["channelQueue", channelId],
        (oldData: any) => ({
          ...oldData,
          data: oldData.data.filter(
            (entry: ChannelQueueOutput) => entry.id !== urlId,
          ),
        }),
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
      ChannelsService.clearUserChannelCompletedQueue({
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
      context.client.setQueryData(
        ["channelQueue", channelId],
        (oldData: any) => ({
          ...oldData,
          data: oldData.data.filter(
            (entry: ChannelQueueOutput) =>
              entry.status !== "Imported" && entry.status !== "Failed",
          ),
        }),
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
              Search for shows or paste URLs to add to the import queue.
            </DialogDescription>
          </DialogHeader>

          <Tabs defaultValue="search" className="flex-1 min-h-0 px-8">
            <TabsList>
              <TabsTrigger value="search">Search</TabsTrigger>
              <TabsTrigger value="urls">Manual URLs</TabsTrigger>
            </TabsList>

            <TabsContent value="search" className="overflow-y-auto py-4">
              <JustWatchSearch channelId={channelId} />
            </TabsContent>

            <TabsContent value="urls" className="overflow-y-auto py-4">
              <div className="space-y-4">
                <h3>Add URLs (one per line)</h3>
                <textarea
                  value={urlsInput}
                  onChange={(e) => setUrlsInput(e.target.value)}
                  placeholder="https://example.com"
                  rows={8}
                  className="w-full rounded-md border border-input px-3 py-2 text-sm outline-none"
                  disabled={addUrlsMutation.isPending}
                />
                <Button
                  onClick={handleSubmit}
                  disabled={addUrlsMutation.isPending}
                >
                  <Plus className="mr-2" />
                  {addUrlsMutation.isPending ? "Adding URLs..." : "Add URLs"}
                </Button>
              </div>
            </TabsContent>
          </Tabs>

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
