// TODO: Validate
import {
  keepPreviousData,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query"
import {
  Antenna,
  Bot,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  ChevronUp,
  Hammer,
  Inbox,
  Info,
  Link2,
  List,
  ListX,
  RefreshCw,
  Search,
  Sparkles,
  Trash2,
  Upload,
} from "lucide-react"
import { useEffect, useState } from "react"
import type {
  ChannelQueueOutput,
  ChannelQueueSort,
  ChannelTitleStats,
  TitleCardDetails,
} from "@/client"
import { ChannelsService } from "@/client"
import {
  type Source,
  type Title,
  TitleCards,
  type TitleGroup,
} from "@/components/Channels/TitleCards"
import {
  CHANNEL_TITLE_PAGE,
  channelTitlesQueryKey,
  useChannelTitlesPage,
} from "@/components/Channels/useChannelTitles"
import { ConfirmDialog } from "@/components/Common/ConfirmDialog"
import { WinBoxModal } from "@/components/Common/WinBoxModal"
import { WrappingTabsList } from "@/components/Common/WrappingTabsList"
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
import { Input } from "@/components/ui/input"
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { Tabs, TabsContent, TabsTrigger } from "@/components/ui/tabs"
import useAuth from "@/hooks/useAuth"
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"
import { AddByUrlPanel } from "./AddByUrlPanel"
import { AISuggestions } from "./AISuggestions"
import { BlacklistedEpisodesDialog } from "./BlacklistedEpisodesDialog"
import { BuilderPanel } from "./BuilderPanel"
import { FeelingLuckyPanel } from "./FeelingLuckyPanel"
import { AdditionalChannelsPanel } from "./ManageSubChannels"
import { TitleSearch } from "./Search"
import { WhitelistManager } from "./WhitelistManager"

const CHANNEL_QUEUE_PAGE = 25

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

// TODO: Validate
function QueueSortButton({
  label,
  column,
  sortBy,
  descending,
  onToggle,
}: {
  label: string
  column: ChannelQueueSort
  sortBy: ChannelQueueSort
  descending: boolean
  onToggle: (column: ChannelQueueSort) => void
}) {
  return (
    <Button
      variant="ghost"
      size="sm"
      className="-ml-2 h-7 px-2 font-medium"
      onClick={() => onToggle(column)}
    >
      {label}
      {sortBy === column &&
        (descending ? (
          <ChevronDown className="h-3.5 w-3.5" />
        ) : (
          <ChevronUp className="h-3.5 w-3.5" />
        ))}
    </Button>
  )
}

// TODO: Validate
function PageSelector({
  pageIndex,
  pageCount,
  onSelect,
}: {
  pageIndex: number
  pageCount: number
  onSelect: (pageIndex: number) => void
}) {
  const [open, setOpen] = useState(false)
  const [value, setValue] = useState("")

  // TODO: Validate
  const submit = () => {
    const page = Number(value)
    if (Number.isInteger(page) && page >= 1 && page <= pageCount) {
      onSelect(page - 1)
      setOpen(false)
    }
  }

  return (
    <Popover
      open={open}
      onOpenChange={(next) => {
        setOpen(next)
        if (next) setValue(String(pageIndex + 1))
      }}
    >
      <PopoverTrigger asChild>
        <Button
          variant="ghost"
          size="sm"
          className="font-normal text-muted-foreground"
        >
          Page {pageIndex + 1} of {pageCount}
        </Button>
      </PopoverTrigger>
      <PopoverContent align="center" className="w-48">
        <div className="flex items-center gap-2">
          <Input
            autoFocus
            type="number"
            min={1}
            max={pageCount}
            value={value}
            onChange={(event) => setValue(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter") submit()
            }}
            className="h-8"
          />
          <Button size="sm" onClick={submit}>
            Go
          </Button>
        </div>
      </PopoverContent>
    </Popover>
  )
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
  const { user } = useAuth()
  const isAdmin = user?.is_superuser ?? false
  const [noteDialogOpen, setNoteDialogOpen] = useState(false)
  const [selectedNote, setSelectedNote] = useState<string | null>(null)
  const [selectedTitle, setSelectedTitle] = useState<TitleGroup | null>(null)
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
  // What the user has typed, and what the listing is actually being read by,
  // which follows it once they have stopped typing.
  const [titleFilter, setTitleFilter] = useState("")
  const [titleQuery, setTitleQuery] = useState("")
  const [queuePageIndex, setQueuePageIndex] = useState(0)
  const [queueFilter, setQueueFilter] = useState("")
  const [queueQuery, setQueueQuery] = useState("")
  const [queueSortBy, setQueueSortBy] = useState<ChannelQueueSort>("created_at")
  const [queueDescending, setQueueDescending] = useState(true)

  // TODO: Validate
  const toggleQueueSort = (column: ChannelQueueSort) => {
    if (column === queueSortBy) {
      setQueueDescending(!queueDescending)
    } else {
      setQueueSortBy(column)
      setQueueDescending(false)
    }
    setQueuePageIndex(0)
  }

  // region Queries

  const { data: queueData, isLoading: isLoadingQueue } = useQuery({
    queryKey: [
      "channelQueue",
      channelId,
      queuePageIndex,
      queueQuery,
      queueSortBy,
      queueDescending,
    ],
    queryFn: () =>
      ChannelsService.getChannelQueue({
        channelId,
        offset: queuePageIndex * CHANNEL_QUEUE_PAGE,
        limit: CHANNEL_QUEUE_PAGE,
        query: queueQuery || undefined,
        sortBy: queueSortBy,
        descending: queueDescending,
      }),
    refetchInterval: queueRefetchInterval,
    // The page a queue is on is read from the total it comes back with, so a
    // page being fetched must not read as a queue of nothing.
    placeholderData: keepPreviousData,
  })

  useEffect(() => {
    const timeout = setTimeout(() => {
      setQueueQuery(queueFilter)
      setQueuePageIndex(0)
    }, 300)
    return () => clearTimeout(timeout)
  }, [queueFilter])

  useEffect(() => {
    const timeout = setTimeout(() => {
      setTitleQuery(titleFilter)
      setPageIndex(0)
    }, 300)
    return () => clearTimeout(timeout)
  }, [titleFilter])

  const { data: titlesPage } = useChannelTitlesPage(
    channelId,
    pageIndex,
    titleQuery,
  )
  const titlesData = titlesPage as unknown as
    | {
        titles: Title[]
        filter_only_titles: Title[]
        sources: Record<string, Source>
        tmdb_titles: Record<string, Title>
        tmdb_sources: Record<string, Source>
        stats: Record<string, ChannelTitleStats>
        details: Record<string, TitleCardDetails>
        total: number
      }
    | undefined
  const titleCount = titlesData?.total ?? 0
  const pageCount = Math.max(1, Math.ceil(titleCount / CHANNEL_TITLE_PAGE))

  useEffect(() => {
    if (titlesData && pageIndex >= pageCount) setPageIndex(pageCount - 1)
  }, [titlesData, pageIndex, pageCount])

  const queueEntries = queueData?.data ?? []
  const queueCount = queueData?.total ?? 0
  const queuePageCount = Math.max(1, Math.ceil(queueCount / CHANNEL_QUEUE_PAGE))
  const pendingQueueCount = queueData?.pending_count ?? 0

  useEffect(() => {
    if (queueData && queuePageIndex >= queuePageCount)
      setQueuePageIndex(queuePageCount - 1)
  }, [queueData, queuePageIndex, queuePageCount])
  const sources: Record<string, Source> = titlesData?.sources || {}
  const tmdbTitles: Record<string, Title> = titlesData?.tmdb_titles || {}
  const tmdbSources: Record<string, Source> = titlesData?.tmdb_sources || {}
  // A card is read under the title's own name, so that is the name the list is
  // in the order of.
  // TODO: Validate
  const titleName = (title: Title) =>
    (title.tmdb_title_id
      ? tmdbTitles[title.tmdb_title_id]?.name
      : title.name) ?? ""
  // TODO: Validate
  const byTitleName = (first: Title, second: Title) =>
    titleName(first).localeCompare(titleName(second))
  const titlesList = (titlesData?.titles ?? []).sort(byTitleName)
  const filterOnlyTitlesList = (titlesData?.filter_only_titles ?? []).sort(
    byTitleName,
  )

  const stats = titlesData?.stats ?? {}
  const details = titlesData?.details ?? {}

  // endregion Queries

  // region Mutations

  const deleteUrlMutation = useMutation({
    mutationFn: (urlId: string) =>
      ChannelsService.deleteChannelQueueUrl({ channelId, urlId }),
    onSuccess: () => showSuccessToast("URL removed from queue"),
    onError: () => showErrorToast("Failed to remove URL from queue"),
    onSettled: (_data, _error, _variables, _onMutateResult, context) =>
      context.client.invalidateQueries({
        queryKey: ["channelQueue", channelId],
      }),
  })

  const retryUrlMutation = useMutation({
    mutationFn: (urlId: string) =>
      ChannelsService.retryChannelQueueUrl({ channelId, urlId }),
    onSuccess: () => showSuccessToast("URL queued for import again"),
    onError: () => showErrorToast("Failed to queue URL for import again"),
    onSettled: (_data, _error, _variables, _onMutateResult, context) =>
      context.client.invalidateQueries({
        queryKey: ["channelQueue", channelId],
      }),
  })

  const retryFailedUrlsMutation = useMutation({
    mutationFn: () =>
      ChannelsService.retryFailedChannelQueueUrls({ channelId }),
    onSuccess: (message) => showSuccessToast(message.message),
    onError: () => showErrorToast("Failed to queue the failed URLs again"),
    onSettled: (_data, _error, _variables, _onMutateResult, context) =>
      context.client.invalidateQueries({
        queryKey: ["channelQueue", channelId],
      }),
  })

  const clearQueueMutation = useMutation({
    mutationFn: () => ChannelsService.clearChannelCompletedQueue({ channelId }),
    onSuccess: () => showSuccessToast("Completed queue entries cleared"),
    onError: () => showErrorToast("Failed to clear queue"),
    onSettled: (_data, _error, _variables, _onMutateResult, context) =>
      context.client.invalidateQueries({
        queryKey: ["channelQueue", channelId],
      }),
  })

  const removeTitleMutation = useMutation({
    mutationFn: (tmdbTitleId: string) =>
      ChannelsService.deleteChannelTitle({ channelId, tmdbTitleId }),
    onMutate: async (tmdbTitleId) => {
      await queryClient.cancelQueries({
        queryKey: ["channel-titles", channelId],
      })
      const previousEpisodesEntries = queryClient.getQueriesData({
        queryKey: ["episodes", channelId],
      })
      const previousTitlesData = queryClient.getQueryData(
        channelTitlesQueryKey(channelId, pageIndex, titleQuery),
      )
      queryClient.setQueryData(
        channelTitlesQueryKey(channelId, pageIndex, titleQuery),
        (oldData: any) => ({
          ...oldData,
          titles: oldData.titles.filter(
            (title: Title) => title.tmdb_title_id !== tmdbTitleId,
          ),
        }),
      )
      showSuccessToast("Title removed successfully")
      return { previousEpisodesEntries, previousTitlesData }
    },
    onError: (error, _tmdbTitleId, context) => {
      for (const [queryKey, data] of context?.previousEpisodesEntries ?? []) {
        queryClient.setQueryData(queryKey as any, data)
      }
      if (context?.previousTitlesData) {
        queryClient.setQueryData(
          channelTitlesQueryKey(channelId, pageIndex, titleQuery),
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
        <WrappingTabsList className={tabsListClassName}>
          <TabsTrigger value="search" className="h-auto">
            <Search className="h-4 w-4" /> Search
          </TabsTrigger>
          <TabsTrigger value="builder" className="h-auto">
            <Hammer className="h-4 w-4" /> Automatic Builder
          </TabsTrigger>
          <TabsTrigger value="bulk" className="h-auto">
            <Upload className="h-4 w-4" /> Import
          </TabsTrigger>
          <TabsTrigger value="titles" className="h-auto">
            <List className="h-4 w-4" /> Edit
            {titleCount > 0 && ` (${titleCount})`}
          </TabsTrigger>
          <TabsTrigger value="queue" className="h-auto">
            <Inbox className="h-4 w-4" /> Queue
            {pendingQueueCount > 0 && ` (${pendingQueueCount})`}
          </TabsTrigger>
          {combinedChannels && (
            <TabsTrigger value="channels" className="h-auto">
              <Antenna className="h-4 w-4" /> Channels
            </TabsTrigger>
          )}
          <TabsTrigger value="ai" className="h-auto">
            <Bot className="h-4 w-4" /> Suggestions
          </TabsTrigger>
        </WrappingTabsList>

        <TabsContent value="search" className={contentClassName}>
          <TitleSearch channelId={channelId} initialQuery={searchQuery} />
        </TabsContent>

        <TabsContent value="builder" className={contentClassName}>
          <BuilderPanel channelId={channelId} />
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
          <div className="flex items-center gap-2">
            <Input
              value={titleFilter}
              onChange={(event) => setTitleFilter(event.target.value)}
              placeholder="Search titles in this channel"
              className="max-w-xs"
            />
            {titleFilter && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setTitleFilter("")}
              >
                Clear
              </Button>
            )}
            <span className="text-sm text-muted-foreground">
              {titleCount} {titleCount === 1 ? "title" : "titles"}
            </span>
          </div>

          {titlesList.length === 0 ? (
            <p className="text-sm text-muted-foreground text-center py-8">
              {titleQuery
                ? `No titles matching "${titleQuery}"`
                : "No titles in this channel"}
            </p>
          ) : (
            <TitleCards
              titles={titlesList}
              sources={sources}
              tmdbTitles={tmdbTitles}
              tmdbSources={tmdbSources}
              stats={stats ?? {}}
              details={details}
              onSelect={(group) =>
                setSelectedTitle(
                  selectedTitle?.tmdbTitleId === group.tmdbTitleId
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
          <WinBoxModal
            open={selectedTitle != null}
            title={`Manage Whitelist - ${selectedTitle?.name || "Unknown Title"}`}
            onClose={() => setSelectedTitle(null)}
          >
            {selectedTitle && (
              <WhitelistManager
                channelId={channelId}
                tmdbTitleId={selectedTitle.tmdbTitleId}
                onClose={() => setSelectedTitle(null)}
              />
            )}
          </WinBoxModal>

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
                tmdbTitles={tmdbTitles}
                tmdbSources={tmdbSources}
                details={details}
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
            <h3>
              Queue ({queueCount} {queueCount === 1 ? "item" : "items"})
            </h3>
            <div className="flex items-center gap-2">
              {isAdmin && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => retryFailedUrlsMutation.mutate()}
                  disabled={retryFailedUrlsMutation.isPending}
                  title="Put every URL this queue gave up on back into it"
                >
                  {retryFailedUrlsMutation.isPending
                    ? "Retrying All..."
                    : "Retry All"}
                </Button>
              )}
              <Button
                variant="outline"
                size="sm"
                onClick={() => clearQueueMutation.mutate()}
                disabled={clearQueueMutation.isPending || queueCount === 0}
              >
                {clearQueueMutation.isPending
                  ? "Clearing Completed Entries..."
                  : "Clear Completed Entries"}
              </Button>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <Input
              value={queueFilter}
              onChange={(event) => setQueueFilter(event.target.value)}
              placeholder="Search URLs in this queue"
              className="max-w-xs"
            />
            {queueFilter && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setQueueFilter("")}
              >
                Clear
              </Button>
            )}
          </div>

          {isLoadingQueue ? (
            <p className="text-sm text-muted-foreground">Loading queue...</p>
          ) : queueEntries.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              {queueQuery
                ? `No URLs matching "${queueQuery}"`
                : "No items in queue"}
            </p>
          ) : (
            <div className="border rounded-lg">
              <Table className="table-fixed">
                <TableHeader>
                  <TableRow>
                    <TableHead>
                      <QueueSortButton
                        label="URL"
                        column="url"
                        sortBy={queueSortBy}
                        descending={queueDescending}
                        onToggle={toggleQueueSort}
                      />
                    </TableHead>
                    <TableHead className="w-25">
                      <QueueSortButton
                        label="Status"
                        column="status"
                        sortBy={queueSortBy}
                        descending={queueDescending}
                        onToggle={toggleQueueSort}
                      />
                    </TableHead>
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
                            onClick={() => retryUrlMutation.mutate(entry.id)}
                            disabled={
                              retryUrlMutation.isPending ||
                              entry.status === "Pending" ||
                              entry.status === "Importing"
                            }
                            title="Import again"
                          >
                            <RefreshCw className="h-4 w-4" />
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

          {queuePageCount > 1 && (
            <div className="flex items-center justify-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setQueuePageIndex(queuePageIndex - 1)}
                disabled={queuePageIndex === 0}
              >
                <ChevronLeft className="h-4 w-4" />
                Previous
              </Button>
              <PageSelector
                pageIndex={queuePageIndex}
                pageCount={queuePageCount}
                onSelect={setQueuePageIndex}
              />
              <Button
                variant="outline"
                size="sm"
                onClick={() => setQueuePageIndex(queuePageIndex + 1)}
                disabled={queuePageIndex >= queuePageCount - 1}
              >
                Next
                <ChevronRight className="h-4 w-4" />
              </Button>
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
            isActive={activeTab === "ai"}
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
          onConfirm={() => removeTitleMutation.mutate(removeTitle.tmdbTitleId)}
        />
      )}

      {/* Blacklisted episodes for filter-only titles */}
      {blacklistTitle && (
        <BlacklistedEpisodesDialog
          channelId={channelId}
          tmdbTitleId={blacklistTitle.tmdbTitleId}
          titleName={blacklistTitle.name || "Unknown Title"}
          isOpen={!!blacklistTitle}
          onClose={() => setBlacklistTitle(null)}
        />
      )}
    </>
  )
}
