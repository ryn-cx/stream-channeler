// TODO: Validate
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import {
  Antenna,
  Info,
  LayoutGrid,
  Link2,
  List,
  ListX,
  Plus,
  Rows3,
  Search,
  Settings,
  Sparkles,
  Trash2,
} from "lucide-react"
import { type ReactNode, useState } from "react"
import Markdown from "react-markdown"
import { remarkAlert } from "remark-github-blockquote-alert"
import "remark-github-blockquote-alert/alert.css"
import type { ChannelQueueOutput } from "@/client"
import { ChannelsService, PluginsService, UsersService } from "@/client"
import { SourceOptionLabel } from "@/components/Common/SourceOptionLabel"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { ButtonGroup } from "@/components/ui/button-group"
import { Card } from "@/components/ui/card"
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
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip"
import { isLoggedIn } from "@/hooks/useAuth"
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"
import { AISuggestions } from "./AISuggestions"
import { BlacklistedEpisodesDialog } from "./BlacklistedEpisodesDialog"
import { FeelingLuckyPanel } from "./FeelingLuckyPanel"
import { AdditionalChannelsPanel } from "./ManageSubChannels"
import { ShowSearch } from "./Search"
import { WhitelistManager } from "./WhitelistManager"

interface Show {
  id: string
  name: string | null
  source_id: string
  url?: string | null
  show_identifier: string
  image_url?: string | null
}

type ShowsView = "table" | "cards"

interface Source {
  key: string
  favicon_url?: string | null
  name: string | null
}

const OTHER_SOURCE_KEY = "Other"

/** The source's favicon, naming the source when it is hovered. */
function SourceFavicon({ source }: { source: Source | undefined }) {
  if (!source?.favicon_url) return null

  const favicon = (
    <img
      src={source.favicon_url}
      alt={`${source.name} favicon`}
      className="size-8 shrink-0"
    />
  )
  if (!source.name) return favicon

  return (
    <Tooltip>
      <TooltipTrigger asChild>{favicon}</TooltipTrigger>
      <TooltipContent>{source.name}</TooltipContent>
    </Tooltip>
  )
}

/**
 * Rank a source by the user's source preferences, lowest first.
 *
 * A source the user has not ordered sits wherever they placed "Other", which is
 * also where every source lands when nobody is signed in.
 */
function useSourceRank(): (source: Source | undefined) => number {
  const { data: preferences } = useQuery({
    queryKey: ["source-preferences"],
    queryFn: () => UsersService.readSourcePreferences(),
    enabled: isLoggedIn(),
  })

  const ranks = new Map(
    (preferences ?? []).map((preference, index) => [
      preference.source_key,
      index,
    ]),
  )
  const otherRank = ranks.get(OTHER_SOURCE_KEY) ?? ranks.size

  return (source) => (source && ranks.get(source.key)) ?? otherRank
}

/**
 * Group shows that are the same title, keeping the order they arrived in.
 *
 * `show_identifier` is what makes the same title on two services one title, so
 * it is the whole of the grouping. It is the TMDB id when the show is linked to
 * TMDB and the plugin's own key for it when it is not, which leaves an unlinked
 * show in a group of its own.
 */
function groupShows(shows: Show[]): Show[][] {
  const groups = new Map<string, Show[]>()
  for (const show of shows) {
    const key = show.show_identifier
    const group = groups.get(key)
    if (group) {
      group.push(show)
    } else {
      groups.set(key, [show])
    }
  }
  return [...groups.values()]
}

/**
 * The show groups a view renders, each ordered by the user's source preferences.
 *
 * @see groupShows for what counts as the same show.
 */
function useShowGroups(shows: Show[], sources: Record<string, Source>) {
  const sourceRank = useSourceRank()

  const bySourceRank = (first: Show, second: Show) =>
    sourceRank(sources[first.source_id]) - sourceRank(sources[second.source_id])

  return {
    groups: groupShows(shows).map((group) => [...group].sort(bySourceRank)),
  }
}

/**
 * The rows of a shows table, with the same show on several services collapsed
 * into one.
 *
 * The same show is usually available on several services, which would otherwise
 * fill the table with rows that read identically. A group shows the name once
 * with a favicon per service.
 */
function ShowRows({
  shows,
  sources,
  renderActions,
}: {
  shows: Show[]
  sources: Record<string, Source>
  renderActions: (show: Show) => ReactNode
}) {
  const { groups } = useShowGroups(shows, sources)

  return (
    <>
      {groups.map((group) => {
        const [firstShow] = group

        return (
          <TableRow key={firstShow.id}>
            <TableCell className="whitespace-normal">
              <div className="flex flex-col gap-1">
                <span className="wrap-break-word">{firstShow.name ?? ""}</span>
                <span className="flex flex-wrap items-center gap-1">
                  {group.map((show) => (
                    <SourceFavicon
                      key={show.id}
                      source={sources[show.source_id]}
                    />
                  ))}
                </span>
              </div>
            </TableCell>
            {/* A channel holds the title rather than one site's copy of it, so
                the actions belong to the group. */}
            <TableCell>{renderActions(firstShow)}</TableCell>
          </TableRow>
        )
      })}
    </>
  )
}

/**
 * The same show groups as `ShowRows`, laid out as cards with their artwork.
 *
 * A card has room to list every service the show is on, so each one is a line of
 * its own with its actions instead of hiding behind an expander.
 */
function ShowCards({
  shows,
  sources,
  renderActions,
}: {
  shows: Show[]
  sources: Record<string, Source>
  renderActions: (show: Show) => ReactNode
}) {
  const { groups } = useShowGroups(shows, sources)

  return (
    <div className="grid gap-3 grid-cols-[repeat(auto-fill,minmax(220px,1fr))]">
      {groups.map((group) => {
        const [firstShow] = group
        const name = firstShow.name ?? ""
        const artwork = group.find((show) => show.image_url)?.image_url

        return (
          <Card key={firstShow.id} className="gap-0 overflow-hidden py-0">
            <div className="aspect-video w-full bg-muted">
              {artwork && (
                <img
                  src={artwork}
                  alt={name}
                  className="size-full object-cover"
                />
              )}
            </div>
            <div className="flex flex-1 flex-col gap-2 p-3">
              <span className="wrap-break-word text-sm font-medium">
                {name}
              </span>
              <div className="space-y-1">
                {group.map((show) => (
                  <div
                    key={show.id}
                    className="flex min-w-0 items-center gap-1 rounded bg-muted/30 px-2 py-1"
                  >
                    <SourceFavicon source={sources[show.source_id]} />
                    <span className="truncate text-xs text-muted-foreground">
                      {sources[show.source_id]?.name ?? name}
                    </span>
                  </div>
                ))}
              </div>
              {/* The channel holds the title, so one set of actions covers every
                  site listed above. */}
              <div className="mt-auto">{renderActions(firstShow)}</div>
            </div>
          </Card>
        )
      })}
    </div>
  )
}

/** The shows of one list, in whichever layout the user picked. */
function ShowsList({
  view,
  shows,
  sources,
  renderActions,
}: {
  view: ShowsView
  shows: Show[]
  sources: Record<string, Source>
  renderActions: (show: Show) => ReactNode
}) {
  if (view === "cards") {
    return (
      <ShowCards
        shows={shows}
        sources={sources}
        renderActions={renderActions}
      />
    )
  }

  return (
    <div className="border rounded-lg">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Show</TableHead>
            <TableHead className="w-25 text-center">Actions</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          <ShowRows
            shows={shows}
            sources={sources}
            renderActions={renderActions}
          />
        </TableBody>
      </Table>
    </div>
  )
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
  const [showsView, setShowsView] = useState<ShowsView>("table")
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
  const showCount = groupShows(showsList).length
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
          <TabsTrigger value="lucky">
            <Sparkles className="h-4 w-4 mr-1" /> I'm Feeling Lucky
          </TabsTrigger>
          <TabsTrigger value="url">
            <Link2 className="h-4 w-4 mr-1" /> Add By URL
          </TabsTrigger>
          <TabsTrigger value="shows">
            <List className="h-4 w-4 mr-1" /> Edit Shows
            {showCount > 0 && ` (${showCount})`}
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

        <TabsContent value="lucky" className={contentClassName}>
          <FeelingLuckyPanel channelId={channelId} />
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
          <div className="flex justify-end">
            <ButtonGroup>
              <Button
                variant={showsView === "table" ? "secondary" : "outline"}
                size="icon-sm"
                onClick={() => setShowsView("table")}
                title="Table view"
              >
                <Rows3 className="h-4 w-4" />
              </Button>
              <Button
                variant={showsView === "cards" ? "secondary" : "outline"}
                size="icon-sm"
                onClick={() => setShowsView("cards")}
                title="Card view"
              >
                <LayoutGrid className="h-4 w-4" />
              </Button>
            </ButtonGroup>
          </div>

          {showsList.length === 0 ? (
            <p className="text-sm text-muted-foreground text-center py-8">
              No shows in this channel
            </p>
          ) : (
            <ShowsList
              view={showsView}
              shows={showsList}
              sources={sources}
              renderActions={(show) => (
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
              )}
            />
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
              <ShowsList
                view={showsView}
                shows={filterOnlyShowsList}
                sources={sources}
                renderActions={(show) => (
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
