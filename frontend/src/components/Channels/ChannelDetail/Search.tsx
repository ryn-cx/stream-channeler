// TODO: Validate
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { Plus, Search } from "lucide-react"
import { useEffect, useState } from "react"
import type {
  PluginSearchResult,
  TMDBMediaInfo,
  TMDBSearchResultItem,
  TMDBWatchProviderItem,
} from "@/client"
import { ChannelsService, PluginsService } from "@/client"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
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

// TMDB is the multi-source aggregator search; every other plugin searches its
// own single platform. This synthetic key selects the aggregator mode.
const TMDB_KEY = "TMDB"

function mediaTypeLabel(mediaType: string): string {
  return mediaType === "movie" ? "Movie" : "TV Show"
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
    <Wrapper
      type={onClick ? "button" : undefined}
      onClick={onClick}
      style={{ width: isLandscape ? LANDSCAPE_WIDTH : PORTRAIT_WIDTH }}
      className={cn(
        "border rounded-lg flex flex-col items-center text-center p-3 shrink-0",
        onClick && "hover:bg-accent/50 transition-colors cursor-pointer",
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
      <p className="font-medium text-sm leading-tight line-clamp-2">{title}</p>
      <div className="text-xs text-muted-foreground mt-1">{subtitle}</div>
      {footer}
    </Wrapper>
  )
}

function PluginResultCard({
  result,
  channelId,
}: {
  result: PluginSearchResult
  channelId: string
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
      footer={<AddToQueueButton url={result.url} channelId={channelId} />}
    />
  )
}

// Opens on top of the media-info modal with a single plugin's search results,
// leaving the underlying modals and the main search untouched.
function PluginSearchModal({
  pluginKey,
  pluginName,
  query,
  channelId,
  onOpenChange,
}: {
  pluginKey: string | null
  pluginName: string | null
  query: string
  channelId: string
  onOpenChange: (open: boolean) => void
}) {
  const { data, isLoading } = useQuery({
    queryKey: ["plugin-search", pluginKey, query],
    queryFn: () =>
      PluginsService.searchPlugin({ pluginKey: pluginKey!, query }),
    enabled: pluginKey != null,
  })
  const results = data?.results ?? []

  return (
    <Dialog open={pluginKey != null} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>{pluginName ?? "Search"} results</DialogTitle>
          <DialogDescription>
            Add a result to grab its importable URL for “{query}”.
          </DialogDescription>
        </DialogHeader>

        {isLoading ? (
          <p className="text-sm text-muted-foreground">Searching…</p>
        ) : results.length > 0 ? (
          <div className="flex flex-wrap gap-3">
            {results.map((result, index) => (
              <PluginResultCard
                key={`${result.url}-${index}`}
                result={result}
                channelId={channelId}
              />
            ))}
          </div>
        ) : (
          <p className="text-sm text-muted-foreground">No results found</p>
        )}
      </DialogContent>
    </Dialog>
  )
}

// Builds the "Movie • 2023 • 8.8★" style metadata line for a media detail.
function metaLine(result: TMDBSearchResultItem, info: TMDBMediaInfo): string[] {
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

function ProviderButton({
  provider,
  onClick,
  href,
}: {
  provider: TMDBWatchProviderItem
  onClick?: () => void
  href?: string
}) {
  const inner = (
    <>
      {provider.icon_url ? (
        <img
          src={provider.icon_url}
          alt={provider.name}
          className="h-8 w-8 rounded"
        />
      ) : null}
      <span className="text-sm">{provider.name}</span>
    </>
  )

  if (href) {
    return (
      <Button asChild variant="outline" className="h-auto gap-2 p-2">
        <a href={href} target="_blank" rel="noreferrer">
          {inner}
        </a>
      </Button>
    )
  }

  return (
    <Button
      type="button"
      variant="outline"
      onClick={onClick}
      className={`h-auto gap-2 p-2 ${onClick ? "" : "cursor-default"}`}
    >
      {inner}
    </Button>
  )
}

function ProviderGroup({
  heading,
  providers,
  muted,
  renderButton,
}: {
  heading: string
  providers: TMDBWatchProviderItem[]
  muted?: boolean
  renderButton: (provider: TMDBWatchProviderItem) => React.ReactNode
}) {
  if (providers.length === 0) return null
  return (
    <div className="flex flex-col gap-1.5">
      <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
        {heading}
      </p>
      <div className={`flex flex-wrap gap-2 ${muted ? "opacity-40" : ""}`}>
        {providers.map(renderButton)}
      </div>
    </div>
  )
}

// Fetches a single title's full detail plus its watch providers on demand, so a
// multi-result search never downloads that data for results the user never opens.
function MediaInfoModal({
  result,
  channelId,
  searchablePluginKeys,
  onOpenChange,
}: {
  result: TMDBSearchResultItem | null
  channelId: string
  searchablePluginKeys: Set<string>
  onOpenChange: (open: boolean) => void
}) {
  const [pluginSearch, setPluginSearch] = useState<{
    pluginKey: string
    pluginName: string
  } | null>(null)
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
  const providers = info?.providers ?? []
  // Plugins we can search in-app show their results in a nested modal; plugins
  // with only a website search page open that page in a new tab instead.
  const inAppSearch = providers.filter(
    (provider) =>
      provider.plugin_key != null &&
      searchablePluginKeys.has(provider.plugin_key),
  )
  const siteSearch = providers.filter(
    (provider) =>
      provider.search_url != null &&
      !(
        provider.plugin_key != null &&
        searchablePluginKeys.has(provider.plugin_key)
      ),
  )
  const manual = providers.filter(
    (provider) =>
      provider.plugin_key != null &&
      provider.search_url == null &&
      !searchablePluginKeys.has(provider.plugin_key),
  )
  const unsupported = providers.filter(
    (provider) => provider.plugin_key == null && provider.search_url == null,
  )

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

              <div className="flex flex-col gap-3">
                <p className="font-semibold">Where to watch</p>
                {providers.length === 0 ? (
                  <p className="text-sm text-muted-foreground">
                    No US streaming sources found.
                  </p>
                ) : (
                  <>
                    <ProviderGroup
                      heading="Search here for the Media"
                      providers={inAppSearch}
                      renderButton={(provider) => (
                        <ProviderButton
                          key={provider.name}
                          provider={provider}
                          onClick={() =>
                            setPluginSearch({
                              pluginKey: provider.plugin_key!,
                              pluginName: provider.name,
                            })
                          }
                        />
                      )}
                    />
                    <ProviderGroup
                      heading="Search the website for the URL"
                      providers={siteSearch}
                      renderButton={(provider) => (
                        <ProviderButton
                          key={provider.name}
                          provider={provider}
                          href={provider.search_url ?? undefined}
                        />
                      )}
                    />
                    <ProviderGroup
                      heading='Supported — add its URL in the "Add by URL" tab'
                      providers={manual}
                      renderButton={(provider) => (
                        <ProviderButton
                          key={provider.name}
                          provider={provider}
                        />
                      )}
                    />
                    <ProviderGroup
                      heading="Not supported"
                      providers={unsupported}
                      muted
                      renderButton={(provider) => (
                        <ProviderButton
                          key={provider.name}
                          provider={provider}
                        />
                      )}
                    />
                  </>
                )}
              </div>
            </>
          ) : (
            <p className="text-sm text-muted-foreground">
              No additional details found.
            </p>
          )}

          <p className="text-xs text-muted-foreground">
            Streaming availability data provided by JustWatch.
          </p>
        </div>
      </DialogContent>

      <PluginSearchModal
        pluginKey={pluginSearch?.pluginKey ?? null}
        pluginName={pluginSearch?.pluginName ?? null}
        query={title}
        channelId={channelId}
        onOpenChange={(open) => {
          if (!open) setPluginSearch(null)
        }}
      />
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

  const [tmdbResults, setTmdbResults] = useState<TMDBSearchResultItem[] | null>(
    null,
  )
  const [pluginResults, setPluginResults] = useState<
    PluginSearchResult[] | null
  >(null)
  const [isSearching, setIsSearching] = useState(false)
  const [selectedResult, setSelectedResult] =
    useState<TMDBSearchResultItem | null>(null)
  const [pluginKey, setPluginKey] = useState(TMDB_KEY)
  const { showErrorToast } = useCustomToast()
  const addUrlMutation = useAddToQueue(channelId)

  const { data: searchablePlugins } = useSearchablePlugins()

  const plugins = searchablePlugins ?? []
  // Plugins that search in-app vs. plugins that only expose a website search
  // page. The latter are offered under a "Manual Search Only" header and open
  // their search page in a new tab instead of showing in-app results.
  const inAppPlugins = plugins.filter((plugin) => !plugin.manual_search_only)
  const manualPlugins = plugins.filter((plugin) => plugin.manual_search_only)
  const searchablePluginKeys = new Set(
    inAppPlugins.map((plugin) => plugin.plugin_key),
  )
  const manualPluginKeys = new Set(
    manualPlugins.map((plugin) => plugin.plugin_key),
  )

  const runSearch = async (key: string, rawQuery: string) => {
    const trimmed = rawQuery.trim()
    if (!trimmed) return

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

    setIsSearching(true)
    setTmdbResults(null)
    setPluginResults(null)
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

      if (key === TMDB_KEY) {
        setTmdbResults(await PluginsService.tmdbSearch({ query: trimmed }))
      } else {
        const response = await PluginsService.searchPlugin({
          pluginKey: key,
          query: trimmed,
        })
        setPluginResults(response.results)
      }
    } catch {
      showErrorToast("Search failed")
    } finally {
      setIsSearching(false)
    }
  }

  const handleSearch = () => runSearch(pluginKey, searchQuery)

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
            <SelectItem value={TMDB_KEY}>TMDB (Search Multiple)</SelectItem>
            {inAppPlugins.map((plugin) => (
              <SelectItem key={plugin.plugin_key} value={plugin.plugin_key}>
                {plugin.name}
              </SelectItem>
            ))}
            {manualPlugins.length > 0 && (
              <SelectGroup>
                <SelectLabel>External Search Only</SelectLabel>
                {manualPlugins.map((plugin) => (
                  <SelectItem key={plugin.plugin_key} value={plugin.plugin_key}>
                    {plugin.name}
                  </SelectItem>
                ))}
              </SelectGroup>
            )}
          </SelectContent>
        </Select>
      </div>

      {tmdbResults && tmdbResults.length > 0 && (
        <div className="flex flex-wrap gap-3">
          {tmdbResults.map((result) => (
            <ResultCard
              key={`${result.media_type}-${result.tmdb_id}`}
              imageUrl={result.image_url}
              title={result.title}
              subtitle={
                <>
                  {mediaTypeLabel(result.media_type)}
                  {result.year && ` (${result.year})`}
                </>
              }
              onClick={() => setSelectedResult(result)}
            />
          ))}
        </div>
      )}

      {pluginResults && pluginResults.length > 0 && (
        <div className="flex flex-wrap gap-3">
          {pluginResults.map((result, index) => (
            <PluginResultCard
              key={`${result.url}-${index}`}
              result={result}
              channelId={channelId}
            />
          ))}
        </div>
      )}

      {(tmdbResults?.length === 0 || pluginResults?.length === 0) &&
        !isSearching &&
        searchQuery && (
          <p className="text-sm text-muted-foreground text-center py-4">
            No results found
          </p>
        )}

      <MediaInfoModal
        result={selectedResult}
        channelId={channelId}
        searchablePluginKeys={searchablePluginKeys}
        onOpenChange={(open) => {
          if (!open) setSelectedResult(null)
        }}
      />
    </div>
  )
}
