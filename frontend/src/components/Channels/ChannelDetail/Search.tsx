// TODO: Validate
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { Check, ChevronLeft, ChevronRight, Plus, Search } from "lucide-react"
import { useCallback, useEffect, useState } from "react"
import type { PluginSearchResult, TMDBMediaInfo } from "@/client"
import { ChannelsService, PluginsService } from "@/client"
import { useAllChannelTitles } from "@/components/Channels/useChannelTitles"
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

// TODO: Validate
function imageUrl(
  size: string,
  path: string | null | undefined,
): string | null {
  return path ? `https://image.tmdb.org/t/p/${size}${path}` : null
}

// TODO: Validate
function releaseYear(value: string | null | undefined): number | null {
  return value ? Number(value.slice(0, 4)) : null
}

// TMDB covers every service rather than one, so it is the source a search starts
// on. Falls back to the first searchable plugin when TMDB is not available.
const DEFAULT_PLUGIN_KEY = "TMDB"

// The title a details modal is open for, built from the plugin result that was
// clicked and the id the plugin issued it under.
export type SelectedTitle = {
  media_identifier: string
  title: string
  // The result's own URL, so the modal queues exactly what its card would.
  url: string
  year?: number | null
  image_url?: string | null
}

// TODO: Validate
function useAddToQueue(channelId: string) {
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (url: string) =>
      ChannelsService.createChannelQueueUrls({
        channelId,
        requestBody: [url],
      }),
    onSuccess: (queue) => {
      showSuccessToast("Title added to import queue")
      queryClient.setQueryData(["channelQueue", channelId], queue)
    },
    onError: handleError.bind(showErrorToast),
  })
}

// A TMDB result's URL is the title's own TMDB page, so it names the same title
// as a channel title's `TMDB tv 123` identifier even when the channel holds that
// title from some other service.
const TMDB_TITLE_URL_PATTERN = /themoviedb\.org\/(tv|movie)\/(\d+)/

// Whether a search result is a title the channel already carries. A result from
// a service is matched on its own URL, and a TMDB result on the title it names.
// TODO: Validate
function useIsInChannel(channelId: string) {
  const { data: titlesData } = useAllChannelTitles(channelId)

  const titles = titlesData?.titles ?? []
  const urls = new Set(titles.map((title) => title.url))
  const tmdbIds = new Set(
    titles.map((title) => title.tmdb_id).filter((id) => id != null),
  )

  return (url: string) => {
    if (urls.has(url)) return true
    const match = TMDB_TITLE_URL_PATTERN.exec(url)
    return match != null && tmdbIds.has(Number(match[2]))
  }
}

// TODO: Validate
function AddToQueueButton({
  url,
  channelId,
}: {
  url: string
  channelId: string
}) {
  const addUrlMutation = useAddToQueue(channelId)
  const isInChannel = useIsInChannel(channelId)

  if (isInChannel(url)) {
    return (
      <Button size="sm" variant="secondary" className="mt-2 w-full" disabled>
        <Check className="h-3 w-3 mr-1" />
        In Channel
      </Button>
    )
  }

  if (addUrlMutation.isSuccess) {
    return (
      <Button size="sm" variant="secondary" className="mt-2 w-full" disabled>
        <Check className="h-3 w-3 mr-1" />
        Added
      </Button>
    )
  }

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
      {addUrlMutation.isPending ? "Adding..." : "Add"}
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

// TODO: Validate
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
            referrerPolicy="no-referrer"
            loading="lazy"
            decoding="async"
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

// TODO: Validate
export function PluginResultCard({
  result,
  channelId,
  onSelect,
  extraFooter,
}: {
  result: PluginSearchResult
  channelId: string
  onSelect?: (result: PluginSearchResult) => void
  extraFooter?: React.ReactNode
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
      // A result carries the id its own plugin issued, so opening the details
      // asks that plugin about it rather than matching it against another.
      onClick={onSelect ? () => onSelect(result) : undefined}
      footer={
        <>
          <AddToQueueButton url={result.url} channelId={channelId} />
          {extraFooter}
        </>
      }
    />
  )
}

// Every source pages its search differently, so the backend hands back an
// opaque cursor for the page after the current one. Keeping the cursor of each
// page that has been visited is what makes stepping back possible.
// TODO: Validate
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

// TODO: Validate
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
// TODO: Validate
function metaLine(
  result: SelectedTitle,
  detail: TMDBMediaInfo["detail"],
): string[] {
  const parts: string[] = []
  const movie = "title" in detail ? detail : null
  const series = "name" in detail ? detail : null

  const year =
    releaseYear(movie ? movie.release_date : series?.first_air_date) ??
    result.year
  if (year) {
    const endYear = releaseYear(series?.last_air_date)
    parts.push(endYear && endYear !== year ? `${year}–${endYear}` : `${year}`)
  }
  if (detail.status) parts.push(detail.status)
  if (series?.number_of_seasons != null) {
    const seasons = `${series.number_of_seasons} season${
      series.number_of_seasons === 1 ? "" : "s"
    }`
    parts.push(
      series.number_of_episodes != null
        ? `${seasons} · ${series.number_of_episodes} episodes`
        : seasons,
    )
  } else if (movie?.runtime != null) {
    parts.push(`${movie.runtime} min`)
  }
  return parts
}

// TODO: Validate
function WatchProviders({
  watchProviders,
}: {
  watchProviders: TMDBMediaInfo["watch_providers"]
}) {
  const streaming = [
    ...(watchProviders?.flatrate ?? []),
    ...(watchProviders?.ads ?? []),
    ...(watchProviders?.free ?? []),
  ]
  const providersByKey = new Map<number | string, (typeof streaming)[number]>()
  for (const provider of streaming) {
    const key = provider.provider_id ?? provider.provider_name ?? ""
    if (!providersByKey.has(key)) providersByKey.set(key, provider)
  }
  const providers = [...providersByKey.values()]

  return (
    <div className="flex flex-col gap-2">
      <h3 className="text-sm font-semibold">Where to watch</h3>
      {providers.length === 0 ? (
        <p className="text-sm text-muted-foreground">
          No streaming services found for this title.
        </p>
      ) : (
        <div className="flex flex-wrap gap-2">
          {providers.map((provider) => {
            const iconUrl = imageUrl("original", provider.logo_path)
            return (
              <span
                key={provider.provider_id ?? provider.provider_name}
                className="flex items-center gap-2 rounded-full border px-2 py-1 text-xs"
              >
                {iconUrl && (
                  <img
                    referrerPolicy="no-referrer"
                    src={iconUrl}
                    alt=""
                    className="size-5 rounded"
                  />
                )}
                {provider.provider_name}
              </span>
            )
          })}
        </div>
      )}
    </div>
  )
}

// Fetches a single title's full detail on demand, so a multi-result search never
// downloads that data for results the user never opens.
// TODO: Validate
export function MediaInfoModal({
  result,
  channelId,
  onOpenChange,
}: {
  result: SelectedTitle | null
  channelId: string
  onOpenChange: (open: boolean) => void
}) {
  const { data: info, isLoading } = useQuery({
    queryKey: ["plugin-media-info", result?.media_identifier],
    queryFn: () =>
      PluginsService.mediaInfo({
        mediaIdentifier: result!.media_identifier,
      }),
    enabled: result != null,
  })

  const detail = info?.detail
  const movie = detail && "title" in detail ? detail : null
  const series = detail && "name" in detail ? detail : null
  const title = movie?.title ?? series?.name ?? result?.title ?? ""
  const posterPath =
    detail?.poster_path ??
    series?.seasons?.find((season) => season.poster_path)?.poster_path
  const backdropUrl = imageUrl("original", detail?.backdrop_path ?? posterPath)
  const posterUrl = imageUrl("w500", posterPath ?? detail?.backdrop_path)

  return (
    <Dialog open={result != null} onOpenChange={onOpenChange}>
      <DialogContent className="gap-0 overflow-hidden p-0 sm:max-w-2xl">
        <div className="relative">
          {backdropUrl ? (
            <img
              referrerPolicy="no-referrer"
              src={backdropUrl}
              alt=""
              className="h-44 w-full object-cover"
            />
          ) : (
            <div className="h-44 w-full bg-muted" />
          )}
          <div className="absolute inset-0 bg-linear-to-t from-background via-background/70 to-transparent" />
          <div className="absolute inset-x-0 bottom-0 flex items-end gap-4 p-4">
            {posterUrl && (
              <img
                referrerPolicy="no-referrer"
                src={posterUrl}
                alt={title}
                className="h-32 w-22 shrink-0 rounded object-cover shadow-lg"
              />
            )}
            <div className="min-w-0 pb-1">
              <DialogTitle className="text-xl font-bold leading-tight">
                {title}
              </DialogTitle>
              {detail?.tagline && (
                <p className="mt-1 text-sm italic text-muted-foreground">
                  {detail.tagline}
                </p>
              )}
            </div>
          </div>
        </div>

        <div className="flex flex-col gap-4 p-6">
          {isLoading ? (
            <p className="text-sm text-muted-foreground">Loading details…</p>
          ) : info && detail ? (
            <>
              <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-sm text-muted-foreground">
                <span>{movie ? "Movie" : "TV Title"}</span>
                {metaLine(result!, detail).map((part) => (
                  <span key={part} className="flex items-center gap-2">
                    <span className="text-muted-foreground/50">•</span>
                    {part}
                  </span>
                ))}
                {detail.vote_average != null && detail.vote_count ? (
                  <span className="flex items-center gap-2">
                    <span className="text-muted-foreground/50">•</span>
                    <span className="font-medium text-foreground">
                      ★ {detail.vote_average.toFixed(1)}
                    </span>
                  </span>
                ) : null}
              </div>

              {detail.genres && detail.genres.length > 0 && (
                <div className="flex flex-wrap gap-1.5">
                  {detail.genres.map((genre) => (
                    <span
                      key={genre.id}
                      className="rounded-full bg-secondary px-2 py-0.5 text-xs text-secondary-foreground"
                    >
                      {genre.name}
                    </span>
                  ))}
                </div>
              )}

              {detail.overview && (
                <p className="text-sm leading-relaxed">{detail.overview}</p>
              )}

              <WatchProviders watchProviders={info.watch_providers ?? null} />
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

interface TitleSearchProps {
  channelId: string
  initialQuery?: string
}

// TODO: Validate
export function TitleSearch({ channelId, initialQuery }: TitleSearchProps) {
  const [searchQuery, setSearchQuery] = useState(initialQuery ?? "")

  useEffect(() => {
    if (initialQuery !== undefined) {
      setSearchQuery(initialQuery)
    }
  }, [initialQuery])

  // The search that results are currently shown for, which is only set once a
  // search has actually been run — the plugin and text in the controls above can
  // be changed without disturbing them.
  const [activeSearch, setActiveSearch] = useState<string | null>(null)
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
    queryKey: ["plugin-search", activeSearch, cursor],
    queryFn: async () => {
      try {
        return await PluginsService.inAppSearch({
          query: activeSearch!,
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

  // A result the plugin gave no id for is one nothing can be asked about.
  // TODO: Validate
  const openResult = useCallback(
    (result: PluginSearchResult) => {
      if (!result.media_identifier) {
        showErrorToast(`No details found for “${result.title}”`)
        return
      }
      setSelectedResult({
        media_identifier: result.media_identifier,
        title: result.title,
        url: result.url,
        year: result.year,
        image_url: result.image_url,
      })
    },
    [showErrorToast],
  )

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

  // TODO: Validate
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
        const { url } = await PluginsService.manualSearchUrl({
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
      setActiveSearch(trimmed)
    } catch {
      showErrorToast("Search failed")
    } finally {
      setIsCheckingUrl(false)
    }
  }

  // TODO: Validate
  const handleSearch = () => runSearch(pluginKey, searchQuery)
  const isSearching = isCheckingUrl || isFetching

  return (
    <div className="space-y-4">
      <div className="flex gap-2">
        <Input
          value={searchQuery}
          onChange={(event) => setSearchQuery(event.target.value)}
          placeholder="Search for a title or movie..."
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
              onSelect={openResult}
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
