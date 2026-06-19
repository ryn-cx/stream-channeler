// TODO: Validate
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { Plus, Search } from "lucide-react"
import { useEffect, useState } from "react"
import { ChannelsService, PluginsService } from "@/client"
import { OpenAPI } from "@/client/core/OpenAPI"
import { request as apiRequest } from "@/client/core/request"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip"
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"

interface SourceInfo {
  name: string
  icon_url: string | null
}

interface SearchResult {
  title: string
  url: string
  year: number | null
  image_url: string | null
  media_type: string | null
  sources: SourceInfo[]
}

interface SearchResponse {
  has_source_selection: boolean
  results: SearchResult[]
}

async function searchBackend(
  pluginKey: string,
  query: string,
): Promise<SearchResponse> {
  return apiRequest<SearchResponse>(OpenAPI, {
    method: "GET",
    url: "/api/v1/plugins/search",
    query: {
      plugin_key: pluginKey,
      query,
    },
    errors: {
      404: "Plugin not found",
      422: "Plugin does not support search",
    },
  })
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

function ExpandedSources({
  result,
  hasSourceSelection,
  channelId,
}: {
  result: SearchResult
  hasSourceSelection: boolean
  channelId: string
}) {
  const [customSource, setCustomSource] = useState("")
  const addUrlMutation = useAddToQueue(channelId)

  const handleAddSource = (sourceName: string) => {
    addUrlMutation.mutate(`${sourceName} ${result.url}`)
  }

  const handleAddAllSources = () => {
    addUrlMutation.mutate(result.url)
  }

  const handleAddCustomSource = () => {
    if (!customSource.trim()) return
    addUrlMutation.mutate(`${customSource.trim()} ${result.url}`, {
      onSuccess: () => {
        setCustomSource("")
      },
    })
  }

  return (
    <div className="p-3 space-y-2">
      {hasSourceSelection && result.sources.length > 0 && (
        <>
          <p className="text-sm text-muted-foreground">
            Choose a source to add:
          </p>
          <div className="flex flex-wrap gap-2">
            <TooltipProvider>
              {result.sources.map((source) => (
                <Tooltip key={source.name}>
                  <TooltipTrigger asChild>
                    <Button
                      variant="outline"
                      onClick={() => handleAddSource(source.name)}
                      disabled={addUrlMutation.isPending}
                      className="h-auto p-2"
                    >
                      {source.icon_url ? (
                        <img
                          src={source.icon_url}
                          alt={source.name}
                          className="h-10 w-10"
                        />
                      ) : (
                        source.name
                      )}
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>{source.name}</TooltipContent>
                </Tooltip>
              ))}
            </TooltipProvider>
          </div>
        </>
      )}
      <Button
        size="sm"
        onClick={handleAddAllSources}
        disabled={addUrlMutation.isPending}
      >
        <Plus className="h-3 w-3 mr-1" />
        {hasSourceSelection ? "Add All Sources" : "Add"}
      </Button>
      {hasSourceSelection && (
        <div className="flex gap-2 pt-1">
          <Input
            placeholder="Custom source name..."
            value={customSource}
            onChange={(event) => setCustomSource(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter") handleAddCustomSource()
            }}
          />
          <Button
            size="sm"
            variant="outline"
            onClick={handleAddCustomSource}
            disabled={addUrlMutation.isPending || !customSource.trim()}
          >
            <Plus className="h-3 w-3 mr-1" />
            Add
          </Button>
        </div>
      )}
    </div>
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
  const [searchResponse, setSearchResponse] = useState<SearchResponse | null>(
    null,
  )
  const [isSearching, setIsSearching] = useState(false)
  const [selectedIndex, setSelectedIndex] = useState<number | null>(null)
  const [pluginKey, setPluginKey] = useState("JustWatch")
  const { showErrorToast } = useCustomToast()
  const addUrlMutation = useAddToQueue(channelId)

  const { data: searchablePlugins } = useQuery({
    queryKey: ["searchable-plugins"],
    queryFn: () =>
      apiRequest<Array<{ plugin_key: string; name: string }>>(OpenAPI, {
        method: "GET",
        url: "/api/v1/plugins/search-information",
      }),
  })

  const handleSearch = async () => {
    const trimmed = searchQuery.trim()
    if (!trimmed) return

    setIsSearching(true)
    setSearchResponse(null)
    setSelectedIndex(null)

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

      const response = await searchBackend(pluginKey, trimmed)
      setSearchResponse(response)
    } catch {
      showErrorToast("Search failed")
    } finally {
      setIsSearching(false)
    }
  }

  const results = searchResponse?.results ?? []
  const plugins = searchablePlugins ?? []

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
      {plugins.length > 0 && (
        <div className="flex items-center gap-2">
          <span className="text-sm text-muted-foreground">
            Search This Website:
          </span>
          <Select value={pluginKey} onValueChange={setPluginKey}>
            <SelectTrigger className="w-50">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {plugins.map((plugin) => (
                <SelectItem key={plugin.plugin_key} value={plugin.plugin_key}>
                  {plugin.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      )}

      {results.length > 0 && (
        <div className="flex flex-wrap gap-3">
          {results.map((result, index) => {
            const hasSourceSelection =
              searchResponse?.has_source_selection ?? false
            const isSelected = selectedIndex === index

            const cardBody = (
              <>
                {result.image_url && (
                  <img
                    src={result.image_url}
                    alt={result.title}
                    className="w-full aspect-2/3 rounded object-cover mb-2"
                  />
                )}
                <p className="font-medium text-sm leading-tight line-clamp-2">
                  {result.title}
                </p>
                <p className="text-xs text-muted-foreground mt-1">
                  {result.media_type}
                  {result.year && ` (${result.year})`}
                </p>
                {!hasSourceSelection && (
                  <AddToQueueButton url={result.url} channelId={channelId} />
                )}
              </>
            )

            const cardClassName = `border rounded-lg flex flex-col items-center text-center p-3 w-36 shrink-0 ${
              hasSourceSelection ? "hover:bg-accent/50 transition-colors" : ""
            } ${isSelected ? "ring-2 ring-primary" : ""}`

            return (
              <div
                key={`${result.url}-${index}`}
                className={`flex gap-3 ${isSelected ? "w-full" : ""}`}
              >
                {hasSourceSelection ? (
                  <button
                    type="button"
                    className={cardClassName}
                    onClick={() => setSelectedIndex(isSelected ? null : index)}
                  >
                    {cardBody}
                  </button>
                ) : (
                  <div className={cardClassName}>{cardBody}</div>
                )}
                {isSelected && (
                  <div className="border rounded-lg flex-1 min-w-0">
                    <ExpandedSources
                      result={result}
                      hasSourceSelection={
                        searchResponse?.has_source_selection ?? false
                      }
                      channelId={channelId}
                    />
                  </div>
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
