// TODO: Validate
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { ChevronLeft, ChevronRight, Plus, Search } from "lucide-react"
import { useCallback, useEffect, useState } from "react"
import type { PluginSearchResult, TMDBMediaInfo } from "@/client"
import { ChannelsService, PluginsService } from "@/client"
import { SourceOptionLabel } from "@/components/Common/SourceOptionLabel"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogTitle } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectLabel,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import useCustomToast from "@/hooks/useCustomToast"
import { useSearchablePlugins } from "@/hooks/useEntities"
import { cn } from "@/lib/utils"
import { handleError } from "@/utils"

function mediaTypeLabel(mediaType: string): string {
  return mediaType === "movie" ? "Movie" : "TV Show"
}

// TMDB covers every service rather than one, so it is the source a search starts
// on. Falls back to the first searchable plugin when TMDB is not available.
const DEFAULT_PLUGIN_KEY = "TMDB"

// The title a details modal is open for, built from the plugin result that was
// clicked and the TMDB id it was matched to.
type SelectedTitle = {
  tmdb_id: number
  media_type: "movie" | "tv"
  title: string
  // The result's own URL, so the modal queues exactly what its card would.
  url: string
  year?: number | null
  image_url?: string | null
}

function useAddToQueue(channelId: string) {
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (url: string) =>
      ChannelsService.createChannelQueueUrls({
        channelId,
        requestBody: [url],
      }),
    onSuccess: () => {
      showSuccessToast("Show added to import queue")
      queryClient.invalidateQueries({
        queryKey: ["channelQueue", channelId],
      })
    },
    onError: handleError.bind(showErrorToast),
  })
}

function AddToQueueButton({
  url,
  channelId,
}: {
  url: string
  channelId: string
}) {
  const addUrlMutation = useAddToQueue(channelId)
  return (
    <Button
      size="sm"
      className="mt-2 w-full"
      onClick={(event) => {
        event.stopPropagation()
        addUrlMutation.mutate(url)
      }}
      disabled={addUrlMutation.isPending}
    >
      <Plus className="h-3 w-3 mr-1" />
      Add
    </Button>
  )
}

// A result card that sizes itself to the image's real aspect ratio. Sources
// return different shapes (2:3 posters, 16:9 stills), so instead of forcing a
// fixed portrait box the card measures each image on load and matches it,
// widening for landscape art so it isn't shrunk into a tall column.
const PORTRAIT_WIDTH = 144
const LANDSCAPE_WIDTH = 256
const DEFAULT_ASPECT_RATIO = 2 / 3

function ResultCard({
  imageUrl,
  title,
  subtitle,
  onClick,
  footer,
}: {
  imageUrl?: string | null
  title: string
  subtitle: React.ReactNode
  onClick?: () => void
  footer?: React.ReactNode
}) {
  const [aspectRatio, setAspectRatio] = useState<number | null>(null)
  const isLandscape = aspectRatio != null && aspectRatio > 1
  const Wrapper = onClick ? "button" : "div"

  return (
    <div
      style={{ width: isLandscape ? LANDSCAPE_WIDTH : PORTRAIT_WIDTH }}
      className={cn(
        "border rounded-lg flex flex-col items-center text-center p-3 shrink-0",
        onClick && "hover:bg-accent/50 transition-colors",
      )}
    >
      {/* The footer holds its own buttons, so it stays outside the clickable
          part of the card rather than nesting buttons inside each other. */}
      <Wrapper
        type={onClick ? "button" : undefined}
        onClick={onClick}
        className={cn(
          "flex flex-col items-center text-center w-full",
          onClick && "cursor-pointer",
        )}
      >
        {imageUrl && (
          <img
            src={imageUrl}
            alt={title}
            onLoad={(event) => {
              const { naturalWidth, naturalHeight } = event.currentTarget
              if (naturalHeight > 0) {
                setAspectRatio(naturalWidth / naturalHeight)
              }
            }}
            style={{ aspectRatio: aspectRatio ?? DEFAULT_ASPECT_RATIO }}
            className="w-full rounded object-cover bg-muted mb-2"
          />
        )}
        <p className="font-medium text-sm leading-tight line-clamp-2">
          {title}
        </p>
        <div className="text-xs text-muted-foreground mt-1">{subtitle}</div>
      </Wrapper>
      {footer}
    </div>
  )
}

function PluginResultCard({
  result,
  channelId,
  onSelect,
}: {
  result: PluginSearchResult
  channelId: string
  onSelect?: (result: PluginSearchResult) => void
}) {
  return (
    <ResultCard
      imageUrl={result.image_url}
      title={result.title}
      subtitle={
        <>
          {result.media_type}
          {result.year && ` (${result.year})`}
        </>
      }
      // A plugin only knows its own service's data, so opening the details
      // means finding the matching TMDB title first.
      onClick={onSelect ? () => onSelect(result) : undefined}
      footer={<AddToQueueButton url={result.url} channelId={channelId} />}
    />
  )
}

// Every source pages its search differently, so the backend hands back an
// opaque cursor for the page after the current one. Keeping the cursor of each
// page that has been visited is what makes stepping back possible.
function useSearchCursors() {
  const [pages, setPages] = useState<{
    cursors: (string | null)[]
    index: number
  }>({ cursors: [null], index: 0 })

  return {
    pageIndex: pages.index,
    cursor: pages.cursors[pages.index],
    reset: useCallback(() => setPages({ cursors: [null], index: 0 }), []),
    goToNextPage: useCallback(
      (nextCursor: string) =>
        setPages(({ cursors, index }) => ({
          cursors: [...cursors.slice(0, index + 1), nextCursor],
          index: index + 1,
        })),
      [],
    ),
    goToPreviousPage: useCallback(
      () =>
        setPages(({ cursors, index }) => ({
          cursors,
          index: Math.max(index - 1, 0),
        })),
      [],
    ),
  }
}

function SearchPager({
  pageIndex,
  nextCursor,
  isLoading,
  onPrevious,
  onNext,
}: {
  pageIndex: number
  nextCursor?: string | null
  isLoading: boolean
  onPrevious: () => void
  onNext: () => void
}) {
  // A single page of results needs no controls at all.
  if (pageIndex === 0 && !nextCursor) return null

  return (
    <div className="flex items-center justify-center gap-3">
      <Button
        variant="outline"
        size="sm"
        onClick={onPrevious}
        disabled={pageIndex === 0 || isLoading}
      >
        <ChevronLeft className="h-4 w-4 mr-1" />
        Previous
      </Button>
      <span className="text-sm text-muted-foreground">
        Page {pageIndex + 1}
      </span>
      <Button
        variant="outline"
        size="sm"
        onClick={onNext}
        disabled={!nextCursor || isLoading}
      >
        Next
        <ChevronRight className="h-4 w-4 ml-1" />
      </Button>
    </div>
  )
}

// Builds the "Movie • 2023 • 8.8★" style metadata line for a media detail.
function metaLine(result: SelectedTitle, info: TMDBMediaInfo): string[] {
  const parts: string[] = []

  const year = info.year ?? result.year
  if (year) {
    parts.push(
      info.end_year && info.end_year !== year
        ? `${year}–${info.end_year}`
        : `${year}`,
    )
  }
  if (info.status) parts.push(info.status)
  if (info.number_of_seasons != null) {
    const seasons = `${info.number_of_seasons} season${
      info.number_of_seasons === 1 ? "" : "s"
    }`
    parts.push(
      info.number_of_episodes != null
        ? `${seasons} · ${info.number_of_episodes} episodes`
        : seasons,
    )
  } else if (info.runtime != null) {
    parts.push(`${info.runtime} min`)
  }
  return parts
}

// Fetches a single title's full detail on demand, so a multi-result search never
// downloads that data for results the user never opens.
function MediaInfoModal({
  result,
  channelId,
  onOpenChange,
}: {
  result: SelectedTitle | null
  channelId: string
  onOpenChange: (open: boolean) => void
}) {
  const { data: info, isLoading } = useQuery({
    queryKey: ["tmdb-media-info", result?.media_type, result?.tmdb_id],
    queryFn: () =>
      PluginsService.tmdbMediaInfo({
        mediaType: result!.media_type,
        tmdbId: result!.tmdb_id,
      }),
    enabled: result != null,
  })

  const title = info?.title ?? result?.title ?? ""

  return (
    <Dialog open={result != null} onOpenChange={onOpenChange}>
      <DialogContent className="gap-0 overflow-hidden p-0 sm:max-w-2xl">
        <div className="relative">
          {info?.backdrop_url ? (
            <img
              src={info.backdrop_url}
              alt=""
              className="h-44 w-full object-cover"
            />
          ) : (
            <div className="h-44 w-full bg-muted" />
          )}
          <div className="absolute inset-0 bg-linear-to-t from-background via-background/70 to-transparent" />
          <div className="absolute inset-x-0 bottom-0 flex items-end gap-4 p-4">
            {info?.poster_url && (
              <img
                src={info.poster_url}
                alt={title}
                className="h-32 w-22 shrink-0 rounded object-cover shadow-lg"
              />
            )}
            <div className="min-w-0 pb-1">
              <DialogTitle className="text-xl font-bold leading-tight">
                {title}
              </DialogTitle>
              {info?.tagline && (
                <p className="mt-1 text-sm italic text-muted-foreground">
                  {info.tagline}
                </p>
              )}
            </div>
          </div>
        </div>

        <div className="flex flex-col gap-4 p-6">
          {isLoading ? (
            <p className="text-sm text-muted-foreground">Loading details…</p>
          ) : info ? (
            <>
              <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-sm text-muted-foreground">
                <span>{result && mediaTypeLabel(result.media_type)}</span>
                {metaLine(result!, info).map((part) => (
                  <span key={part} className="flex items-center gap-2">
                    <span className="text-muted-foreground/50">•</span>
                    {part}
                  </span>
                ))}
                {info.rating != null && info.vote_count ? (
                  <span className="flex items-center gap-2">
                    <span className="text-muted-foreground/50">•</span>
                    <span className="font-medium text-foreground">
                      ★ {info.rating.toFixed(1)}
                    </span>
                  </span>
                ) : null}
              </div>

              {info.genres && info.genres.length > 0 && (
                <div className="flex flex-wrap gap-1.5">
                  {info.genres.map((genre) => (
                    <span
                      key={genre}
                      className="rounded-full bg-secondary px-2 py-0.5 text-xs text-secondary-foreground"
                    >
                      {genre}
                    </span>
                  ))}
                </div>
              )}

              {info.overview && (
                <p className="text-sm leading-relaxed">{info.overview}</p>
              )}
            </>
          ) : (
            <p className="text-sm text-muted-foreground">
              No additional details found.
            </p>
          )}

          {/* Importing works out where a title can be watched on its own, so
              there is nothing to pick here — one button queues the title. */}
          {result && (
            <AddToQueueButton url={result.url} channelId={channelId} />
          )}

          <p className="text-xs text-muted-foreground">
            Streaming availability data provided by JustWatch.
          </p>
        </div>
      </DialogContent>
    </Dialog>
  )
}

interface ShowSearchProps {
  channelId: string
  initialQuery?: string
}

export function ShowSearch({ channelId, initialQuery }: ShowSearchProps) {
  const [searchQuery, setSearchQuery] = useState(initialQuery ?? "")

  useEffect(() => {
    if (initialQuery !== undefined) {
      setSearchQuery(initialQuery)
    }
  }, [initialQuery])

  // The search that results are currently shown for, which is only set once a
  // search has actually been run — the plugin and text in the controls above can
  // be changed without disturbing them.
  const [activeSearch, setActiveSearch] = useState<{
    pluginKey: string
    query: string
  } | null>(null)
  const [isCheckingUrl, setIsCheckingUrl] = useState(false)
  const [selectedResult, setSelectedResult] = useState<SelectedTitle | null>(
    null,
  )
  const [pluginKey, setPluginKey] = useState("")
  const { showErrorToast } = useCustomToast()
  const addUrlMutation = useAddToQueue(channelId)
  const { pageIndex, cursor, reset, goToNextPage, goToPreviousPage } =
    useSearchCursors()

  const { data: searchPage, isFetching } = useQuery({
    queryKey: [
      "plugin-search",
      activeSearch?.pluginKey,
      activeSearch?.query,
      cursor,
    ],
    queryFn: async () => {
      try {
        return await PluginsService.searchPlugin({
          pluginKey: activeSearch!.pluginKey,
          query: activeSearch!.query,
          cursor,
        })
      } catch (error) {
        showErrorToast("Search failed")
        throw error
      }
    },
    enabled: activeSearch != null,
  })
  const pluginResults = activeSearch ? (searchPage?.results ?? null) : null

  // A plugin result carries no TMDB id, so the matching title is looked up when
  // the card is opened rather than for every result of every search.
  const tmdbMatchMutation = useMutation({
    mutationFn: async (result: PluginSearchResult) => {
      const match = await PluginsService.tmdbMatch({
        title: result.title,
        mediaType: result.media_type === "Movie" ? "movie" : "tv",
        year: result.year,
      })
      return { match, result }
    },
    onSuccess: ({ match, result }) => {
      if (!match) {
        showErrorToast(`No details found for “${result.title}”`)
        return
      }
      setSelectedResult({
        tmdb_id: match.tmdb_id,
        media_type: match.media_type,
        title: result.title,
        url: result.url,
        year: result.year,
        image_url: result.image_url,
      })
    },
    onError: () => showErrorToast("Failed to load details"),
  })

  const { data: searchablePlugins } = useSearchablePlugins()

  const plugins = searchablePlugins ?? []
  // Plugins that search in-app vs. plugins that only expose a website search
  // page. The latter are offered under a "Manual Search Only" header and open
  // their search page in a new tab instead of showing in-app results.
  const inAppPlugins = plugins.filter((plugin) => !plugin.manual_search_only)
  const manualPlugins = plugins.filter((plugin) => plugin.manual_search_only)
  const manualPluginKeys = new Set(
    manualPlugins.map((plugin) => plugin.plugin_key),
  )

  useEffect(() => {
    if (!pluginKey && inAppPlugins.length > 0) {
      const preferred = inAppPlugins.find(
        (plugin) => plugin.plugin_key === DEFAULT_PLUGIN_KEY,
      )
      setPluginKey((preferred ?? inAppPlugins[0]).plugin_key)
    }
  }, [pluginKey, inAppPlugins])

  const runSearch = async (key: string, rawQuery: string) => {
    const trimmed = rawQuery.trim()
    if (!key || !trimmed) return

    // Manual-search-only plugins have no in-app search; open their website's
    // search page in a new tab. The tab is opened synchronously so the browser
    // keeps it tied to the click and doesn't block it as a popup.
    if (manualPluginKeys.has(key)) {
      const newTab = window.open("", "_blank")
      if (newTab) newTab.opener = null
      try {
        const { url } = await PluginsService.searchUrl({
          pluginKey: key,
          query: trimmed,
        })
        if (url) {
          if (newTab) newTab.location.href = url
        } else {
          newTab?.close()
          showErrorToast("No search page available")
        }
      } catch {
        newTab?.close()
        showErrorToast("Search failed")
      }
      return
    }

    setIsCheckingUrl(true)
    setActiveSearch(null)
    setSelectedResult(null)

    try {
      // Ask the backend whether any plugin accepts the input as an importable
      // URL. If so, skip search and queue it directly.
      const match = await PluginsService.matchUrl({ url: trimmed })
      if (match.matched) {
        addUrlMutation.mutate(trimmed, {
          onSuccess: () => {
            setSearchQuery("")
          },
        })
        return
      }

      // A new search always starts from the first page.
      reset()
      setActiveSearch({ pluginKey: key, query: trimmed })
    } catch {
      showErrorToast("Search failed")
    } finally {
      setIsCheckingUrl(false)
    }
  }

  const handleSearch = () => runSearch(pluginKey, searchQuery)
  const isSearching = isCheckingUrl || isFetching

  return (
    <div className="space-y-4">
      <div className="flex gap-2">
        <Input
          value={searchQuery}
          onChange={(event) => setSearchQuery(event.target.value)}
          placeholder="Search for a show or movie..."
          onKeyDown={(event) => {
            if (event.key === "Enter") handleSearch()
          }}
        />
        <Button
          onClick={handleSearch}
          disabled={isSearching || addUrlMutation.isPending}
        >
          <Search className="h-4 w-4 mr-2" />
          {isSearching ? "Searching..." : "Search"}
        </Button>
      </div>
      <div className="flex items-center gap-2">
        <span className="text-sm text-muted-foreground">Search:</span>
        <Select value={pluginKey} onValueChange={setPluginKey}>
          <SelectTrigger className="w-50">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {inAppPlugins.map((plugin) => (
              <SelectItem key={plugin.plugin_key} value={plugin.plugin_key}>
                <SourceOptionLabel
                  name={plugin.name}
                  faviconUrl={plugin.favicon_url}
                />
              </SelectItem>
            ))}
            {manualPlugins.length > 0 && (
              <SelectGroup>
                <SelectLabel>External Search Only</SelectLabel>
                {manualPlugins.map((plugin) => (
                  <SelectItem key={plugin.plugin_key} value={plugin.plugin_key}>
                    <SourceOptionLabel
                      name={plugin.name}
                      faviconUrl={plugin.favicon_url}
                    />
                  </SelectItem>
                ))}
              </SelectGroup>
            )}
          </SelectContent>
        </Select>
      </div>

      {pluginResults && pluginResults.length > 0 && (
        <div className="flex flex-wrap gap-3">
          {pluginResults.map((result, index) => (
            <PluginResultCard
              key={`${result.url}-${index}`}
              result={result}
              channelId={channelId}
              onSelect={(selected) => tmdbMatchMutation.mutate(selected)}
            />
          ))}
        </div>
      )}

      {pluginResults?.length === 0 && !isSearching && searchQuery && (
        <p className="text-sm text-muted-foreground text-center py-4">
          No results found
        </p>
      )}

      {activeSearch && (
        <SearchPager
          pageIndex={pageIndex}
          nextCursor={searchPage?.next_cursor}
          isLoading={isSearching}
          onPrevious={goToPreviousPage}
          onNext={() =>
            searchPage?.next_cursor && goToNextPage(searchPage.next_cursor)
          }
        />
      )}

      <MediaInfoModal
        result={selectedResult}
        channelId={channelId}
        onOpenChange={(open) => {
          if (!open) setSelectedResult(null)
        }}
      />

    </div>
  )
}
