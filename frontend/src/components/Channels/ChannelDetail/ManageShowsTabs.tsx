// TODO: Validate
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import {
  Antenna,
  Info,
  Link2,
  List,
  ListX,
  Plus,
  Search,
  Settings,
  Sparkles,
  Trash2,
} from "lucide-react"
import { useState } from "react"
import Markdown from "react-markdown"
import { remarkAlert } from "remark-github-blockquote-alert"
import "remark-github-blockquote-alert/alert.css"
import type { ChannelQueueOutput } from "@/client"
import { ChannelsService, PluginsService } from "@/client"
import { SourceOptionLabel } from "@/components/Common/SourceOptionLabel"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
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
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"
import { AISuggestions } from "./AISuggestions"
import { BlacklistedEpisodesDialog } from "./BlacklistedEpisodesDialog"
import { AdditionalChannelsPanel } from "./ManageSubChannels"
import { ShowSearch } from "./Search"
import { WhitelistManager } from "./WhitelistManager"

interface Show {
  id: string
  name: string | null
  source_id: string
  url?: string | null
}

interface Source {
  favicon_url?: string | null
  name: string | null
}

function getStatusBadgeVariant(status: string) {
  switch (status) {
    case "Imported":
      return "default"
    case "Failed":
      return "destructive"
    case "Importing":
      return "secondary"
    default:
      return "outline"
  }
}

interface ManageShowsTabsProps {
  channelId: string
  /** Padding applied around each tab's content. Callers can override to match
   * the surrounding layout (e.g. the modal uses `px-8 py-4`). */
  contentClassName?: string
  /** List class applied to the TabsList. Defaults to no horizontal padding. */
  tabsListClassName?: string
  /** Poll interval (ms) for the queue. Defaults to undefined (no polling). */
  queueRefetchInterval?: number
  /** When provided, adds an owner-only "Combined Channels" tab. */
  combinedChannels?: {
    isLoggedIn?: boolean
  }
  /** Called to close the surrounding modal, e.g. after saving a tab's action. */
  onRequestClose?: () => void
}

export function ManageShowsTabs({
  channelId,
  contentClassName = "overflow-y-auto flex-1 min-h-0 py-4",
  tabsListClassName,
  queueRefetchInterval,
  combinedChannels,
  onRequestClose,
}: ManageShowsTabsProps) {
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const queryClient = useQueryClient()
  const [urlsInput, setUrlsInput] = useState("")
  const [selectedPlugin, setSelectedPlugin] = useState<string | null>(null)
  const [noteDialogOpen, setNoteDialogOpen] = useState(false)
  const [selectedNote, setSelectedNote] = useState<string | null>(null)
  const [selectedShowId, setSelectedShowId] = useState<string | null>(null)
  const [blacklistShowId, setBlacklistShowId] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<string>("search")
  const [searchQuery, setSearchQuery] = useState<string | undefined>(undefined)

  // region Queries

  const { data: urlImportPlugins } = useQuery({
    queryKey: ["url-import-plugins"],
    queryFn: () => PluginsService.importUrlInformation(),
  })

  const { data: queueData, isLoading: isLoadingQueue } = useQuery({
    queryKey: ["channelQueue", channelId],
    queryFn: () => ChannelsService.getChannelQueue({ channelId }),
    refetchInterval: queueRefetchInterval,
  })

  const { data: showsData } = useQuery({
    queryKey: ["channel-shows", channelId],
    queryFn: () =>
      ChannelsService.getChannelShows({ channelId }) as unknown as Promise<{
        shows: Show[]
        filter_only_shows: Show[]
        sources: Record<string, Source>
      }>,
  })

  const queueEntries = queueData ?? []
  const pendingQueueCount = queueEntries.filter(
    (entry: ChannelQueueOutput) =>
      entry.status !== "Imported" && entry.status !== "Failed",
  ).length
  const showsList = (showsData?.shows ?? []).sort((a, b) =>
    (a.name ?? "").localeCompare(b.name ?? ""),
  )
  const filterOnlyShowsList = (showsData?.filter_only_shows ?? []).sort(
    (a, b) => (a.name ?? "").localeCompare(b.name ?? ""),
  )
  const sources: Record<string, Source> = showsData?.sources || {}
  const shows: Record<string, Show> = {
    ...(showsData?.shows
      ? Object.fromEntries(showsData.shows.map((show) => [show.id, show]))
      : {}),
    ...(showsData?.filter_only_shows
      ? Object.fromEntries(
          showsData.filter_only_shows.map((show) => [show.id, show]),
        )
      : {}),
  }

  // endregion Queries

  // region Mutations

  const addUrlsMutation = useMutation({
    mutationFn: (urls: string[]) =>
      ChannelsService.createChannelQueueUrls({
        channelId,
        requestBody: urls,
      }),
    onMutate: async (urls, context) => {
      await context.client.cancelQueries({
        queryKey: ["channelQueue", channelId],
      })
      const previousQueue = context.client.getQueryData([
        "channelQueue",
        channelId,
      ])
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
      return { previousQueue }
    },
    onError: (error, _urls, onMutateResult, context) => {
      context.client.setQueryData(
        ["channelQueue", channelId],
        onMutateResult?.previousQueue,
      )
      handleError.call(showErrorToast, error as any)
    },
    onSettled: (_data, _error, _variables, _onMutateResult, context) =>
      context.client.invalidateQueries({
        queryKey: ["channelQueue", channelId],
      }),
  })

  const deleteUrlMutation = useMutation({
    mutationFn: (urlId: string) =>
      ChannelsService.deleteChannelQueueUrl({ channelId, urlId }),
    onMutate: async (urlId, context) => {
      await context.client.cancelQueries({
        queryKey: ["channelQueue", channelId],
      })
      const previousQueue = context.client.getQueryData([
        "channelQueue",
        channelId,
      ])
      context.client.setQueryData(["channelQueue", channelId], (oldData: any) =>
        oldData.filter((entry: ChannelQueueOutput) => entry.id !== urlId),
      )
      showSuccessToast("URL removed from queue")
      return { previousQueue }
    },
    onError: (_error, _urlId, onMutateResult, context) => {
      context.client.setQueryData(
        ["channelQueue", channelId],
        onMutateResult?.previousQueue,
      )
      showErrorToast("Failed to remove URL from queue")
    },
    onSettled: (_data, _error, _variables, _onMutateResult, context) =>
      context.client.invalidateQueries({
        queryKey: ["channelQueue", channelId],
      }),
  })

  const clearQueueMutation = useMutation({
    mutationFn: () => ChannelsService.clearChannelCompletedQueue({ channelId }),
    onMutate: async (_variables, context) => {
      await context.client.cancelQueries({
        queryKey: ["channelQueue", channelId],
      })
      const previousQueue = context.client.getQueryData([
        "channelQueue",
        channelId,
      ])
      context.client.setQueryData(["channelQueue", channelId], (oldData: any) =>
        oldData.filter(
          (entry: ChannelQueueOutput) =>
            entry.status !== "Imported" && entry.status !== "Failed",
        ),
      )
      showSuccessToast("Completed queue entries cleared")
      return { previousQueue }
    },
    onError: (_error, _variables, onMutateResult, context) => {
      context.client.setQueryData(
        ["channelQueue", channelId],
        onMutateResult?.previousQueue,
      )
      showErrorToast("Failed to clear queue")
    },
    onSettled: (_data, _error, _variables, _onMutateResult, context) =>
      context.client.invalidateQueries({
        queryKey: ["channelQueue", channelId],
      }),
  })

  const removeShowMutation = useMutation({
    mutationFn: (showId: string) =>
      ChannelsService.deleteChannelShow({ channelId, showId }),
    onMutate: async (showId) => {
      await queryClient.cancelQueries({
        queryKey: ["channel-shows", channelId],
      })
      const previousEpisodesEntries = queryClient.getQueriesData({
        queryKey: ["episodes", channelId],
      })
      const previousShowsData = queryClient.getQueryData([
        "channel-shows",
        channelId,
      ])
      queryClient.setQueryData(
        ["channel-shows", channelId],
        (oldData: any) => ({
          ...oldData,
          shows: oldData.shows.filter((show: Show) => show.id !== showId),
        }),
      )
      showSuccessToast("Show removed successfully")
      return { previousEpisodesEntries, previousShowsData }
    },
    onError: (error, _showId, context) => {
      for (const [queryKey, data] of context?.previousEpisodesEntries ?? []) {
        queryClient.setQueryData(queryKey as any, data)
      }
      if (context?.previousShowsData) {
        queryClient.setQueryData(
          ["channel-shows", channelId],
          context.previousShowsData,
        )
      }
      handleError.call(showErrorToast, error as any)
    },
    onSettled: () => {
      queryClient.invalidateQueries({
        queryKey: ["channel-shows", channelId],
      })
      queryClient.invalidateQueries({
        queryKey: ["episodes", channelId],
      })
    },
  })

  // endregion Mutations

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

  const handleRemoveShow = (showId: string) => {
    if (
      confirm(
        "Are you sure you want to remove this show from the channel? This will remove all episodes from this show.",
      )
    ) {
      removeShowMutation.mutate(showId)
    }
  }

  return (
    <>
      <Tabs
        value={activeTab}
        onValueChange={setActiveTab}
        className="flex-1 min-h-0 flex flex-col"
      >
        <TabsList className={tabsListClassName}>
          <TabsTrigger value="search">
            <Search className="h-4 w-4 mr-1" /> Search
          </TabsTrigger>
          <TabsTrigger value="url">
            <Link2 className="h-4 w-4 mr-1" /> Add By URL
          </TabsTrigger>
          <TabsTrigger value="shows">
            <List className="h-4 w-4 mr-1" /> Edit Shows
            {showsList.length > 0 && ` (${showsList.length})`}
          </TabsTrigger>
          <TabsTrigger value="queue">
            Queue{pendingQueueCount > 0 && ` (${pendingQueueCount})`}
          </TabsTrigger>
          {combinedChannels && (
            <TabsTrigger value="channels">
              <Antenna className="h-4 w-4 mr-1" /> Combined Channels
            </TabsTrigger>
          )}
          <TabsTrigger value="ai">
            <Sparkles className="h-4 w-4 mr-1" /> AI Suggestions
          </TabsTrigger>
        </TabsList>

        <TabsContent value="search" className={contentClassName}>
          <ShowSearch channelId={channelId} initialQuery={searchQuery} />
        </TabsContent>

        <TabsContent value="url" className={contentClassName}>
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
                {addUrlsMutation.isPending ? "Adding URLs..." : "Add URLs"}
              </Button>
            </div>
          </div>
        </TabsContent>

        <TabsContent value="shows" className={`${contentClassName} space-y-6`}>
          {showsList.length === 0 ? (
            <p className="text-sm text-muted-foreground text-center py-8">
              No shows in this channel
            </p>
          ) : (
            <div className="border rounded-lg">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Show</TableHead>
                    <TableHead className="w-25 text-center">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {showsList.map((show) => {
                    const source = sources[show.source_id]
                    return (
                      <TableRow key={show.id}>
                        <TableCell className="whitespace-normal">
                          <div className="flex items-center gap-2">
                            {source?.favicon_url && (
                              <img
                                src={source.favicon_url}
                                alt={`${source.name} favicon`}
                                className="size-4 shrink-0"
                              />
                            )}
                            <span className="wrap-break-word">
                              {show.name ?? ""}
                            </span>
                          </div>
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center justify-center gap-1">
                            <Button
                              variant="ghost"
                              size="icon-sm"
                              onClick={() => setSelectedShowId(show.id)}
                              title="Manage whitelist"
                            >
                              <Settings className="h-4 w-4" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="icon-sm"
                              onClick={() => handleRemoveShow(show.id)}
                              disabled={removeShowMutation.isPending}
                              title="Remove show"
                            >
                              <Trash2 className="h-4 w-4" />
                            </Button>
                          </div>
                        </TableCell>
                      </TableRow>
                    )
                  })}
                </TableBody>
              </Table>
            </div>
          )}

          {filterOnlyShowsList.length > 0 && (
            <div className="space-y-2">
              <div>
                <h3 className="text-sm font-semibold">Filter-only shows</h3>
                <p className="text-xs text-muted-foreground">
                  Shows that aren't part of this channel but have episodes
                  blacklisted from channels included here.
                </p>
              </div>
              <div className="border rounded-lg">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Show</TableHead>
                      <TableHead className="w-25 text-center">
                        Actions
                      </TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {filterOnlyShowsList.map((show) => {
                      const source = sources[show.source_id]
                      return (
                        <TableRow key={show.id}>
                          <TableCell className="whitespace-normal">
                            <div className="flex items-center gap-2">
                              {source?.favicon_url && (
                                <img
                                  src={source.favicon_url}
                                  alt={`${source.name} favicon`}
                                  className="size-4 shrink-0"
                                />
                              )}
                              <span className="wrap-break-word">
                                {show.name ?? ""}
                              </span>
                            </div>
                          </TableCell>
                          <TableCell>
                            <div className="flex items-center justify-center gap-1">
                              <Button
                                variant="ghost"
                                size="icon-sm"
                                onClick={() => setBlacklistShowId(show.id)}
                                title="View blacklisted episodes"
                              >
                                <ListX className="h-4 w-4" />
                              </Button>
                              <Button
                                variant="ghost"
                                size="icon-sm"
                                onClick={() => handleRemoveShow(show.id)}
                                disabled={removeShowMutation.isPending}
                                title="Remove show"
                              >
                                <Trash2 className="h-4 w-4" />
                              </Button>
                            </div>
                          </TableCell>
                        </TableRow>
                      )
                    })}
                  </TableBody>
                </Table>
              </div>
            </div>
          )}
        </TabsContent>

        <TabsContent value="queue" className={`${contentClassName} space-y-4`}>
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
              <Table className="table-fixed">
                <TableHeader>
                  <TableRow>
                    <TableHead>URL</TableHead>
                    <TableHead className="w-25">Status</TableHead>
                    <TableHead className="w-25 text-center">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {queueEntries.map((entry: ChannelQueueOutput) => (
                    <TableRow key={entry.id}>
                      <TableCell className="truncate" title={entry.url}>
                        {entry.url}
                      </TableCell>
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
        </TabsContent>

        {combinedChannels && (
          <TabsContent value="channels" className={contentClassName}>
            <AdditionalChannelsPanel
              channelId={channelId}
              isLoggedIn={combinedChannels.isLoggedIn}
              onSaved={onRequestClose}
            />
          </TabsContent>
        )}

        <TabsContent
          value="ai"
          forceMount
          className={`${contentClassName} data-[state=inactive]:hidden`}
        >
          <AISuggestions
            channelId={channelId}
            onRequestSearch={(title) => {
              setSearchQuery(title)
              setActiveTab("search")
            }}
          />
        </TabsContent>
      </Tabs>

      {/* Note Dialog */}
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

      {/* Whitelist Manager */}
      {selectedShowId && (
        <WhitelistManager
          channelId={channelId}
          showId={selectedShowId}
          showName={shows[selectedShowId]?.name || "Unknown Show"}
          isOpen={!!selectedShowId}
          onClose={() => setSelectedShowId(null)}
        />
      )}

      {/* Blacklisted episodes for filter-only shows */}
      {blacklistShowId && (
        <BlacklistedEpisodesDialog
          channelId={channelId}
          showId={blacklistShowId}
          showName={shows[blacklistShowId]?.name || "Unknown Show"}
          isOpen={!!blacklistShowId}
          onClose={() => setBlacklistShowId(null)}
        />
      )}
    </>
  )
}
