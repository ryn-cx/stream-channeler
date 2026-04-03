// TODO: Validate
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { Loader2, Plus, Search } from "lucide-react"
import { useEffect, useState } from "react"
import { ChannelsService } from "@/client"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"
import { URL_TITLE_DETAILS_QUERY } from "./justwatch-queries"

// region JustWatch

const JUSTWATCH_GRAPHQL_URL = "https://apis.justwatch.com/graphql"
const JUSTWATCH_IMAGES_BASE_URL = "https://images.justwatch.com"

const JUSTWATCH_SEARCH_QUERY = `query GetSearchResults($country: Country!, $language: Language!, $first: Int!, $searchQuery: String, $location: String!) {
  searchTitles(
    country: $country
    first: $first
    filter: {searchQuery: $searchQuery, includeTitlesWithoutUrl: true}
    source: $location
  ) {
    edges {
      node {
        ...SuggestedTitle
        __typename
      }
      __typename
    }
    __typename
  }
}

fragment SuggestedTitle on MovieOrShow {
  __typename
  id
  objectType
  objectId
  content(country: $country, language: $language) {
    fullPath
    title
    originalReleaseYear
    posterUrl
    __typename
  }
}`

const EXCLUDED_PACKAGES = [
  "3ca",
  "als",
  "amo",
  "cic",
  "cnv",
  "cut",
  "daf",
  "koc",
  "kod",
  "mrp",
  "mte",
  "mvt",
  "nxp",
  "opl",
  "org",
  "ply",
  "rvl",
  "tak",
  "tbv",
  "tf1",
  "uat",
  "vld",
  "wa4",
  "wdt",
  "yot",
  "yrk",
]

interface JustWatchNode {
  id: string
  objectType: string
  content: {
    fullPath: string
    title: string
    originalReleaseYear: number | null
    posterUrl: string | null
  }
}

interface BuyBoxOffer {
  package: {
    shortName: string
    clearName: string
    icon: string
  }
}

interface UrlTitleDetailsResponse {
  data: {
    urlV2: {
      node: {
        flatrate?: BuyBoxOffer[]
        free?: BuyBoxOffer[]
        fast?: BuyBoxOffer[]
        buy?: BuyBoxOffer[]
        rent?: BuyBoxOffer[]
      }
    }
  }
}

interface SourceInfo {
  shortName: string
  clearName: string
  iconUrl: string
}

function extractUniqueSources(response: UrlTitleDetailsResponse): SourceInfo[] {
  const node = response.data.urlV2.node
  const allOffers = [
    ...(node.flatrate ?? []),
    ...(node.free ?? []),
    ...(node.fast ?? []),
    ...(node.buy ?? []),
    ...(node.rent ?? []),
  ]
  const seen = new Map<string, SourceInfo>()
  for (const offer of allOffers) {
    if (!seen.has(offer.package.shortName)) {
      seen.set(offer.package.shortName, {
        shortName: offer.package.shortName,
        clearName: offer.package.clearName,
        iconUrl: `${JUSTWATCH_IMAGES_BASE_URL}${offer.package.icon.replace("{format}", "png")}`,
      })
    }
  }
  return [...seen.values()]
}

async function searchJustWatch(query: string): Promise<SearchResult[]> {
  const response = await fetch(JUSTWATCH_GRAPHQL_URL, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      operationName: "GetSearchResults",
      variables: {
        country: "US",
        language: "en",
        searchQuery: query,
        first: 4,
        location: "SearchSuggester",
      },
      query: JUSTWATCH_SEARCH_QUERY,
    }),
  })
  const data = await response.json()
  return data.data.searchTitles.edges.map((edge: { node: JustWatchNode }) => {
    const node = edge.node
    const posterUrl = node.content.posterUrl
      ? `${JUSTWATCH_IMAGES_BASE_URL}${node.content.posterUrl.replace("{profile}", "s166").replace("{format}", "webp")}`
      : null
    return {
      id: node.id,
      title: node.content.title,
      type: node.objectType === "SHOW" ? "TV Show" : "Movie",
      year: node.content.originalReleaseYear,
      posterUrl,
      provider: "justwatch" as const,
      fullPath: node.content.fullPath,
    }
  })
}

// endregion JustWatch

// region Shared types

interface SearchResult {
  id: string
  title: string
  type: string
  year: number | null
  posterUrl: string | null
  fullPath: string
}

// endregion Shared types

// region Components

function useAddToQueue(channelId: string) {
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (url: string) =>
      ChannelsService.createUserChannelQueueUrls({
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

function JustWatchExpandedSources({
  result,
  channelId,
}: {
  result: SearchResult
  channelId: string
}) {
  const [sources, setSources] = useState<SourceInfo[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [customUrl, setCustomUrl] = useState("")
  const { showErrorToast } = useCustomToast()
  const addUrlMutation = useAddToQueue(channelId)

  useEffect(() => {
    let cancelled = false

    async function fetchOffers() {
      try {
        const response = await fetch(JUSTWATCH_GRAPHQL_URL, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            operationName: "GetUrlTitleDetails",
            variables: {
              fullPath: result.fullPath,
              site: "www",
              country: "US",
              language: "en",
              platform: "WEB",
              fallbackToForeignOffers: true,
              excludePackages: EXCLUDED_PACKAGES,
              episodeMaxLimit: 20,
              excludeTextRecommendationTitle: true,
              first: 10,
            },
            query: URL_TITLE_DETAILS_QUERY,
          }),
        })
        const data: UrlTitleDetailsResponse = await response.json()
        if (!cancelled) {
          setSources(extractUniqueSources(data))
        }
      } catch {
        if (!cancelled) {
          showErrorToast("Failed to load sources")
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false)
        }
      }
    }

    fetchOffers()
    return () => {
      cancelled = true
    }
  }, [result.fullPath, showErrorToast])

  const buildUrl = (sourceName: string) => {
    return `${sourceName} justwatch.com${result.fullPath}`
  }

  const handleAddSource = (sourceClearName: string) => {
    addUrlMutation.mutate(buildUrl(sourceClearName))
  }

  const handleAddAllSources = () => {
    const url = `justwatch.com${result.fullPath}`
    addUrlMutation.mutate(url)
  }

  const handleAddCustomSource = () => {
    if (!customUrl.trim()) return
    addUrlMutation.mutate(buildUrl(customUrl.trim()), {
      onSuccess: () => setCustomUrl(""),
    })
  }

  if (isLoading) {
    return (
      <div className="border-t p-3 flex items-center gap-2 text-sm text-muted-foreground">
        <Loader2 className="h-4 w-4 animate-spin" />
        Loading sources...
      </div>
    )
  }

  return (
    <div className="border-t p-3 space-y-2">
      {sources.length > 0 ? (
        <>
          <p className="text-sm text-muted-foreground">
            Choose a source to add:
          </p>
          <div className="flex flex-wrap gap-2">
            {sources.map((source) => (
              <Button
                key={source.shortName}
                size="sm"
                variant="outline"
                onClick={() => handleAddSource(source.clearName)}
                disabled={addUrlMutation.isPending}
                className="gap-1.5"
              >
                <img
                  src={source.iconUrl}
                  alt={source.clearName}
                  className="h-4 w-4 rounded-sm"
                />
                {source.clearName}
              </Button>
            ))}
          </div>
        </>
      ) : (
        <p className="text-sm text-muted-foreground">
          No streaming sources available
        </p>
      )}
      <Button
        size="sm"
        onClick={handleAddAllSources}
        disabled={addUrlMutation.isPending}
      >
        <Plus className="h-3 w-3 mr-1" />
        Add All Sources
      </Button>
      <div className="flex gap-2 pt-1">
        <Input
          placeholder="Custom source name..."
          value={customUrl}
          onChange={(event) => setCustomUrl(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter") handleAddCustomSource()
          }}
        />
        <Button
          size="sm"
          variant="outline"
          onClick={handleAddCustomSource}
          disabled={addUrlMutation.isPending || !customUrl.trim()}
        >
          <Plus className="h-3 w-3 mr-1" />
          Add
        </Button>
      </div>
    </div>
  )
}

interface SearchComponentProps {
  channelId: string
}

export function JustWatchSearch({ channelId }: SearchComponentProps) {
  const [searchQuery, setSearchQuery] = useState("")
  const [results, setResults] = useState<SearchResult[]>([])
  const [isSearching, setIsSearching] = useState(false)
  const [selectedResultId, setSelectedResultId] = useState<string | null>(null)
  const { showErrorToast } = useCustomToast()

  const handleSearch = async () => {
    if (!searchQuery.trim()) return
    setIsSearching(true)
    setResults([])
    setSelectedResultId(null)

    try {
      setResults(await searchJustWatch(searchQuery.trim()))
    } catch {
      showErrorToast("Failed to search JustWatch")
    } finally {
      setIsSearching(false)
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex gap-2">
        <Input
          value={searchQuery}
          onChange={(event) => setSearchQuery(event.target.value)}
          placeholder="Search JustWatch..."
          onKeyDown={(event) => {
            if (event.key === "Enter") handleSearch()
          }}
        />
        <Button onClick={handleSearch} disabled={isSearching}>
          <Search className="h-4 w-4 mr-2" />
          {isSearching ? "Searching..." : "Search"}
        </Button>
      </div>

      {results.length > 0 && (
        <div className="space-y-2">
          {results.map((result) => {
            const isSelected = selectedResultId === result.id

            return (
              <div
                key={result.id}
                className="border rounded-lg overflow-hidden"
              >
                <button
                  type="button"
                  className="flex items-center gap-3 p-3 w-full text-left hover:bg-accent/50 transition-colors"
                  onClick={() =>
                    setSelectedResultId(isSelected ? null : result.id)
                  }
                >
                  {result.posterUrl && (
                    <img
                      src={result.posterUrl}
                      alt={result.title}
                      className="w-12 h-18 rounded object-cover shrink-0"
                    />
                  )}
                  <div className="flex-1 min-w-0">
                    <p className="font-medium truncate">{result.title}</p>
                    <p className="text-sm text-muted-foreground">
                      {result.type}
                      {result.year && ` (${result.year})`}
                    </p>
                  </div>
                </button>

                {isSelected && (
                  <JustWatchExpandedSources
                    result={result}
                    channelId={channelId}
                  />
                )}
              </div>
            )
          })}
        </div>
      )}

      {results.length === 0 && !isSearching && searchQuery && (
        <p className="text-sm text-muted-foreground text-center py-4">
          No results found
        </p>
      )}
    </div>
  )
}

// endregion Components
