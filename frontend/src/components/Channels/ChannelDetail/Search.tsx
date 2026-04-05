// TODO: Validate
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { Plus, Search } from "lucide-react"
import { useState } from "react"
import { ChannelsService } from "@/client"
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
      onSuccess: () => setCustomSource(""),
    })
  }

  return (
    <div className="border-t p-3 space-y-2">
      {hasSourceSelection && result.sources.length > 0 && (
        <>
          <p className="text-sm text-muted-foreground">
            Choose a source to add:
          </p>
          <div className="flex flex-wrap gap-2">
            {result.sources.map((source) => (
              <Button
                key={source.name}
                size="sm"
                variant="outline"
                onClick={() => handleAddSource(source.name)}
                disabled={addUrlMutation.isPending}
                className="gap-1.5"
              >
                {source.icon_url && (
                  <img
                    src={source.icon_url}
                    alt={source.name}
                    className="h-4 w-4 rounded-sm"
                  />
                )}
                {source.name}
              </Button>
            ))}
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
}

export function ShowSearch({ channelId }: ShowSearchProps) {
  const [searchQuery, setSearchQuery] = useState("")
  const [searchResponse, setSearchResponse] = useState<SearchResponse | null>(
    null,
  )
  const [isSearching, setIsSearching] = useState(false)
  const [selectedIndex, setSelectedIndex] = useState<number | null>(null)
  const [pluginKey, setPluginKey] = useState("JustWatch")
  const { showErrorToast } = useCustomToast()

  const { data: searchablePlugins } = useQuery({
    queryKey: ["searchable-plugins"],
    queryFn: () =>
      apiRequest<Array<{ plugin_key: string; name: string }>>(OpenAPI, {
        method: "GET",
        url: "/api/v1/plugins/supports-search",
      }),
  })

  const handleSearch = async () => {
    if (!searchQuery.trim()) return
    setIsSearching(true)
    setSearchResponse(null)
    setSelectedIndex(null)

    try {
      const response = await searchBackend(pluginKey, searchQuery.trim())
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
        <Button onClick={handleSearch} disabled={isSearching}>
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
        <div className="space-y-2">
          {results.map((result, index) => {
            const isSelected = selectedIndex === index

            return (
              <div
                key={`${result.url}-${index}`}
                className="border rounded-lg overflow-hidden"
              >
                <button
                  type="button"
                  className="flex items-center gap-3 p-3 w-full text-left hover:bg-accent/50 transition-colors"
                  onClick={() => setSelectedIndex(isSelected ? null : index)}
                >
                  {result.image_url && (
                    <img
                      src={result.image_url}
                      alt={result.title}
                      className="w-12 h-18 rounded object-cover shrink-0"
                    />
                  )}
                  <div className="flex-1 min-w-0">
                    <p className="font-medium truncate">{result.title}</p>
                    <p className="text-sm text-muted-foreground">
                      {result.media_type}
                      {result.year && ` (${result.year})`}
                    </p>
                  </div>
                </button>

                {isSelected && (
                  <ExpandedSources
                    result={result}
                    hasSourceSelection={
                      searchResponse?.has_source_selection ?? false
                    }
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
