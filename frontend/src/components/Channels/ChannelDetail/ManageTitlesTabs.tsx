// TODO: Validate
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import {
  Antenna,
  Bot,
  ChevronLeft,
  ChevronRight,
  Inbox,
  Info,
  Link2,
  List,
  ListX,
  Maximize2,
  Minimize2,
  Search,
  Sparkles,
  Trash2,
  Upload,
} from "lucide-react"
import { useEffect, useState } from "react"
import type { ChannelQueueOutput } from "@/client"
import { ChannelsService } from "@/client"
import {
  type Source,
  type Title,
  TitleCards,
  type TitleGroup,
} from "@/components/Channels/TitleCards"
import {
  CHANNEL_TITLE_PAGE,
  useChannelTitleStats,
  useChannelTitlesPage,
} from "@/components/Channels/useChannelTitles"
import { ConfirmDialog } from "@/components/Common/ConfirmDialog"
import { ModalContent } from "@/components/Common/ModalContent"
import { TooltipIconButton } from "@/components/Common/TooltipIconButton"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { ButtonGroup } from "@/components/ui/button-group"
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
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
import { cn } from "@/lib/utils"
import { handleError } from "@/utils"
import { AddByUrlPanel } from "./AddByUrlPanel"
import { AISuggestions } from "./AISuggestions"
import { BlacklistedEpisodesDialog } from "./BlacklistedEpisodesDialog"
import { FeelingLuckyPanel } from "./FeelingLuckyPanel"
import { AdditionalChannelsPanel } from "./ManageSubChannels"
import { TitleSearch } from "./Search"
import { WhitelistManager } from "./WhitelistManager"

// TODO: Validate
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

interface ManageTitlesTabsProps {
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
  /** Called with the tab now being read, so a modal can size itself to it. */
  onActiveTabChange?: (tab: string) => void
}

// TODO: Validate
export function ManageTitlesTabs({
  channelId,
  contentClassName = "no-scrollbar -mx-6 max-h-[50vh] overflow-y-auto px-6 py-4",
  tabsListClassName,
  queueRefetchInterval,
  combinedChannels,
  onRequestClose,
  onActiveTabChange,
}: ManageTitlesTabsProps) {
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const queryClient = useQueryClient()
  const [noteDialogOpen, setNoteDialogOpen] = useState(false)
  const [selectedNote, setSelectedNote] = useState<string | null>(null)
  const [selectedTitle, setSelectedTitle] = useState<TitleGroup | null>(null)
  const [isTitleFullScreen, setIsTitleFullScreen] = useState(false)
  const [blacklistTitle, setBlacklistTitle] = useState<TitleGroup | null>(null)
  const [removeTitle, setRemoveTitle] = useState<TitleGroup | null>(null)
  const [activeTab, setActiveTabState] = useState<string>("search")
  // TODO: Validate
  const setActiveTab = (tab: string) => {
    setActiveTabState(tab)
    onActiveTabChange?.(tab)
  }
  const [searchQuery, setSearchQuery] = useState<string | undefined>(undefined)
  const [bulkMode, setBulkMode] = useState<"url" | "name">("url")
  const [pageIndex, setPageIndex] = useState(0)

  // region Queries

  const { data: queueData, isLoading: isLoadingQueue } = useQuery({
    queryKey: ["channelQueue", channelId],
    queryFn: () => ChannelsService.getChannelQueue({ channelId }),
    refetchInterval: queueRefetchInterval,
  })

  const { data: titlesPage } = useChannelTitlesPage(channelId, pageIndex)
  const titlesData = titlesPage as unknown as
    | {
        titles: Title[]
        filter_only_titles: Title[]
        sources: Record<string, Source>
        canonical_titles: Record<string, Title>
        canonical_sources: Record<string, Source>
        total: number
      }
    | undefined
  const titleCount = titlesData?.total ?? 0
  const pageCount = Math.max(1, Math.ceil(titleCount / CHANNEL_TITLE_PAGE))

  useEffect(() => {
    if (pageIndex >= pageCount) setPageIndex(pageCount - 1)
  }, [pageIndex, pageCount])

  const queueEntries = queueData ?? []
  const pendingQueueCount = queueEntries.filter(
    (entry: ChannelQueueOutput) =>
      entry.status !== "Imported" && entry.status !== "Failed",
  ).length
  const sources: Record<string, Source> = titlesData?.sources || {}
  const canonicalTitles: Record<string, Title> =
    titlesData?.canonical_titles || {}
  const canonicalSources: Record<string, Source> =
    titlesData?.canonical_sources || {}
  // A card is read under the title's own name, so that is the name the list is
  // in the order of.
  // TODO: Validate
  const titleName = (title: Title) =>
    (title.canonical_title_id
      ? canonicalTitles[title.canonical_title_id]?.name
      : title.name) ?? ""
  // TODO: Validate
  const byTitleName = (first: Title, second: Title) =>
    titleName(first).localeCompare(titleName(second))
  const titlesList = (titlesData?.titles ?? []).sort(byTitleName)
  const filterOnlyTitlesList = (titlesData?.filter_only_titles ?? []).sort(
    byTitleName,
  )

  const listedCanonicalTitleIds = [
    ...new Set(titlesList.map((title) => title.canonical_title_id ?? title.id)),
  ]
  const { data: stats } = useChannelTitleStats(
    channelId,
    listedCanonicalTitleIds,
  )

  // endregion Queries

  // region Mutations

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
          (entry: ChannelQueueOutput) => entry.status !== "Imported",
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

  const removeTitleMutation = useMutation({
    mutationFn: (canonicalTitleId: string) =>
      ChannelsService.deleteChannelTitle({ channelId, canonicalTitleId }),
    onMutate: async (canonicalTitleId) => {
      await queryClient.cancelQueries({
        queryKey: ["channel-titles", channelId],
      })
      const previousEpisodesEntries = queryClient.getQueriesData({
        queryKey: ["episodes", channelId],
      })
      const previousTitlesData = queryClient.getQueryData([
        "channel-titles",
        channelId,
        pageIndex,
      ])
      queryClient.setQueryData(
        ["channel-titles", channelId, pageIndex],
        (oldData: any) => ({
          ...oldData,
          titles: oldData.titles.filter(
            (title: Title) => title.canonical_title_id !== canonicalTitleId,
          ),
        }),
      )
      showSuccessToast("Title removed successfully")
      return { previousEpisodesEntries, previousTitlesData }
    },
    onError: (error, _canonicalTitleId, context) => {
      for (const [queryKey, data] of context?.previousEpisodesEntries ?? []) {
        queryClient.setQueryData(queryKey as any, data)
      }
      if (context?.previousTitlesData) {
        queryClient.setQueryData(
          ["channel-titles", channelId, pageIndex],
          context.previousTitlesData,
        )
      }
      handleError.call(showErrorToast, error as any)
    },
    onSettled: () => {
      queryClient.invalidateQueries({
        queryKey: ["channel-titles", channelId],
      })
      queryClient.invalidateQueries({
        queryKey: ["episodes", channelId],
      })
      queryClient.invalidateQueries({
        queryKey: ["channel-title-stats", channelId],
      })
    },
  })

  // endregion Mutations

  // TODO: Validate
  const showNote = (note: string | null | undefined) => {
    setSelectedNote(note || null)
    setNoteDialogOpen(true)
  }

  // TODO: Validate
  const handleRemoveTitle = (group: TitleGroup) => {
    setRemoveTitle(group)
  }

  return (
    <>
      <Tabs
        value={activeTab}
        onValueChange={setActiveTab}
        className="flex-1 min-h-0 flex flex-col"
      >
        <TabsList
          className={cn(
            "h-auto w-auto self-stretch flex-nowrap justify-start gap-1",
            "overflow-x-auto no-scrollbar *:flex-none",
            tabsListClassName,
          )}
        >
          <TabsTrigger value="search">
            <Search className="h-4 w-4" /> Search
          </TabsTrigger>
          <TabsTrigger value="bulk">
            <Upload className="h-4 w-4" /> Import
          </TabsTrigger>
          <TabsTrigger value="titles">
            <List className="h-4 w-4" /> Edit
            {titleCount > 0 && ` (${titleCount})`}
          </TabsTrigger>
          <TabsTrigger value="queue">
            <Inbox className="h-4 w-4" /> Queue
            {pendingQueueCount > 0 && ` (${pendingQueueCount})`}
          </TabsTrigger>
          {combinedChannels && (
            <TabsTrigger value="channels">
              <Antenna className="h-4 w-4" /> Channels
            </TabsTrigger>
          )}
          <TabsTrigger value="ai">
            <Bot className="h-4 w-4" /> Suggestions
          </TabsTrigger>
        </TabsList>

        <TabsContent value="search" className={contentClassName}>
          <TitleSearch channelId={channelId} initialQuery={searchQuery} />
        </TabsContent>

        <TabsContent value="bulk" className={`${contentClassName} space-y-3`}>
          <ButtonGroup>
            <Button
              variant={bulkMode === "url" ? "default" : "outline"}
              size="sm"
              onClick={() => setBulkMode("url")}
              aria-pressed={bulkMode === "url"}
            >
              <Link2 className="h-4 w-4 mr-1" /> By URL
            </Button>
            <Button
              variant={bulkMode === "name" ? "default" : "outline"}
              size="sm"
              onClick={() => setBulkMode("name")}
              aria-pressed={bulkMode === "name"}
            >
              <Sparkles className="h-4 w-4 mr-1" /> By Name
            </Button>
          </ButtonGroup>

          {bulkMode === "url" ? (
            <AddByUrlPanel channelId={channelId} />
          ) : (
            <FeelingLuckyPanel channelId={channelId} />
          )}
        </TabsContent>

        <TabsContent value="titles" className={`${contentClassName} space-y-6`}>
          {titlesList.length === 0 ? (
            <p className="text-sm text-muted-foreground text-center py-8">
              No titles in this channel
            </p>
          ) : (
            <TitleCards
              titles={titlesList}
              sources={sources}
              canonicalTitles={canonicalTitles}
              canonicalSources={canonicalSources}
              stats={stats ?? {}}
              onSelect={(group) =>
                setSelectedTitle(
                  selectedTitle?.canonicalTitleId === group.canonicalTitleId
                    ? null
                    : group,
                )
              }
              renderActions={(group) => (
                <div className="flex items-center justify-center gap-1">
                  <Button
                    variant="ghost"
                    size="icon-sm"
                    onClick={() => handleRemoveTitle(group)}
                    disabled={removeTitleMutation.isPending}
                    title="Remove title"
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              )}
            />
          )}

          {pageCount > 1 && (
            <div className="flex items-center justify-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setPageIndex(pageIndex - 1)}
                disabled={pageIndex === 0}
              >
                <ChevronLeft className="h-4 w-4" />
                Previous
              </Button>
              <span className="text-sm text-muted-foreground">
                Page {pageIndex + 1} of {pageCount}
              </span>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setPageIndex(pageIndex + 1)}
                disabled={pageIndex >= pageCount - 1}
              >
                Next
                <ChevronRight className="h-4 w-4" />
              </Button>
            </div>
          )}

          {/*
            A title's seasons and episodes are a table of their own, so opening
            one gets a window of its own rather than pushing the list it was
            opened from out to the width the table wants.
          */}
          <Dialog
            open={selectedTitle != null}
            onOpenChange={(open) => {
              if (!open) setSelectedTitle(null)
            }}
          >
            <ModalContent
              size={isTitleFullScreen ? "full" : "4xl"}
              className={
                isTitleFullScreen
                  ? "max-h-none h-[calc(100dvh-2rem)] flex flex-col overflow-hidden"
                  : "max-h-[85vh] flex flex-col overflow-hidden"
              }
            >
              <DialogHeader className="px-8">
                <DialogTitle>
                  {selectedTitle?.name || "Unknown Title"}
                </DialogTitle>
              </DialogHeader>
              {selectedTitle && (
                <div className="no-scrollbar flex-1 min-h-0 overflow-y-auto px-8 py-4">
                  <WhitelistManager
                    channelId={channelId}
                    canonicalTitleId={selectedTitle.canonicalTitleId}
                    titleName={selectedTitle.name || "Unknown Title"}
                    onClose={() => setSelectedTitle(null)}
                  />
                </div>
              )}

              <TooltipIconButton
                label={
                  isTitleFullScreen ? "Shrink to a window" : "Fill the screen"
                }
                icon={isTitleFullScreen ? <Minimize2 /> : <Maximize2 />}
                size="icon-sm"
                className="absolute left-4 top-4 z-10"
                onClick={() => setIsTitleFullScreen(!isTitleFullScreen)}
              />
            </ModalContent>
          </Dialog>

          {filterOnlyTitlesList.length > 0 && (
            <div className="space-y-2">
              <div>
                <h3 className="text-sm font-semibold">Filter-only titles</h3>
                <p className="text-xs text-muted-foreground">
                  Titles that aren't part of this channel but have episodes
                  blacklisted from channels included here.
                </p>
              </div>
              <TitleCards
                titles={filterOnlyTitlesList}
                sources={sources}
                canonicalTitles={canonicalTitles}
                canonicalSources={canonicalSources}
                renderActions={(group) => (
                  <div className="flex items-center justify-center gap-1">
                    <Button
                      variant="ghost"
                      size="icon-sm"
                      onClick={() => setBlacklistTitle(group)}
                      title="View blacklisted episodes"
                    >
                      <ListX className="h-4 w-4" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon-sm"
                      onClick={() => handleRemoveTitle(group)}
                      disabled={removeTitleMutation.isPending}
                      title="Remove title"
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                )}
              />
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
                            title="Title note"
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

      {removeTitle && (
        <ConfirmDialog
          open={!!removeTitle}
          onOpenChange={(open) => {
            if (!open) setRemoveTitle(null)
          }}
          title="Remove Title"
          description={`Are you sure you want to remove "${removeTitle.name || "this title"}" from the channel? This will remove all episodes from this title.`}
          confirmLabel="Remove"
          onConfirm={() =>
            removeTitleMutation.mutate(removeTitle.canonicalTitleId)
          }
        />
      )}

      {/* Blacklisted episodes for filter-only titles */}
      {blacklistTitle && (
        <BlacklistedEpisodesDialog
          channelId={channelId}
          canonicalTitleId={blacklistTitle.canonicalTitleId}
          titleName={blacklistTitle.name || "Unknown Title"}
          isOpen={!!blacklistTitle}
          onClose={() => setBlacklistTitle(null)}
        />
      )}
    </>
  )
}
