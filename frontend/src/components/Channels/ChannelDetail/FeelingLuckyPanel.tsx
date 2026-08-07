// TODO: Validate
import { useQueryClient } from "@tanstack/react-query"
import { Check, Sparkles, X } from "lucide-react"
import { useEffect, useState } from "react"

import { ChannelsService, PluginsService } from "@/client"
import { SourceOptionLabel } from "@/components/Common/SourceOptionLabel"
import { Button } from "@/components/ui/button"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Textarea } from "@/components/ui/textarea"
import useCustomToast from "@/hooks/useCustomToast"
import { useSearchablePlugins } from "@/hooks/useEntities"
import { handleError } from "@/utils"

/** What became of one title the search was run for. */
interface LuckyOutcome {
  title: string
  /** The title of the result that was taken, or null when nothing was found. */
  matched: string | null
  url: string | null
  failed: boolean
}

// TMDB covers every service rather than one, so it is the source a search starts
// on. Falls back to the first searchable plugin when TMDB is not available.
const DEFAULT_PLUGIN_KEY = "TMDB"

function parseTitles(text: string): string[] {
  return text
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean)
}

/**
 * Search for several titles at once and queue the first result of each.
 *
 * One title per line, since a title can have a comma in it but not a line
 * break. Each is searched on its own so one title finding nothing does not stop
 * the rest, and every result is reported rather than only the count, so a wrong
 * first match is visible instead of silently queued.
 */
export function FeelingLuckyPanel({ channelId }: { channelId: string }) {
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const [titlesText, setTitlesText] = useState("")
  const [outcomes, setOutcomes] = useState<LuckyOutcome[]>([])
  const [isRunning, setIsRunning] = useState(false)
  const [pluginKey, setPluginKey] = useState("")

  const { data: searchablePlugins } = useSearchablePlugins()
  // A plugin with no in-app search returns nothing to take a first result from,
  // so there is nothing to feel lucky about and it is not offered here.
  const inAppPlugins = (searchablePlugins ?? []).filter(
    (plugin) => !plugin.manual_search_only,
  )

  useEffect(() => {
    if (!pluginKey && inAppPlugins.length > 0) {
      const preferred = inAppPlugins.find(
        (plugin) => plugin.plugin_key === DEFAULT_PLUGIN_KEY,
      )
      setPluginKey((preferred ?? inAppPlugins[0]).plugin_key)
    }
  }, [pluginKey, inAppPlugins])

  const titles = parseTitles(titlesText)

  const run = async () => {
    setIsRunning(true)
    setOutcomes([])

    const found: LuckyOutcome[] = []
    // Searched one at a time so a plugin is not asked for every title at once,
    // and so the list fills in as it goes rather than all at the end.
    for (const title of titles) {
      try {
        const page = await PluginsService.searchPlugin({
          pluginKey,
          query: title,
        })
        const first = page.results[0]
        found.push({
          title,
          matched: first?.title ?? null,
          url: first?.url ?? null,
          failed: false,
        })
      } catch {
        found.push({ title, matched: null, url: null, failed: true })
      }
      setOutcomes([...found])
    }

    const urls = found
      .map((outcome) => outcome.url)
      .filter((url): url is string => url !== null)

    if (urls.length > 0) {
      try {
        await ChannelsService.createChannelQueueUrls({
          channelId,
          requestBody: urls,
        })
        queryClient.invalidateQueries({ queryKey: ["channelQueue", channelId] })
        showSuccessToast(
          `Added ${urls.length} of ${found.length} to the import queue`,
        )
      } catch (error) {
        handleError.call(
          showErrorToast,
          error as Parameters<typeof handleError>[0],
        )
      }
    } else if (found.length > 0) {
      showErrorToast("Nothing was found for any of those titles")
    }

    setIsRunning(false)
  }

  return (
    <div className="border rounded-lg p-4 space-y-3">
      <p className="text-sm text-muted-foreground">
        One title per line. Each is searched and its first result is added to
        the import queue.
      </p>

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
          </SelectContent>
        </Select>
      </div>

      <Textarea
        value={titlesText}
        onChange={(event) => setTitlesText(event.target.value)}
        placeholder={"Cowboy Bebop\nGintama\nLaid-Back Camp"}
        rows={6}
        aria-label="Titles to search"
        disabled={isRunning}
      />

      {outcomes.length > 0 && (
        <div className="max-h-64 space-y-1 overflow-y-auto rounded-lg border p-2 text-sm">
          {outcomes.map((outcome) => (
            <div key={outcome.title} className="flex items-start gap-2">
              {outcome.url ? (
                <Check className="mt-0.5 size-4 shrink-0 text-green-500" />
              ) : (
                <X className="mt-0.5 size-4 shrink-0 text-destructive" />
              )}
              <span className="min-w-0 whitespace-normal wrap-break-word">
                <span className="font-medium">{outcome.title}</span>
                {outcome.matched ? (
                  <span className="text-muted-foreground">
                    {" → "}
                    {outcome.matched}
                  </span>
                ) : (
                  <span className="text-muted-foreground">
                    {outcome.failed ? " — search failed" : " — no results"}
                  </span>
                )}
              </span>
            </div>
          ))}
        </div>
      )}

      <Button
        onClick={run}
        disabled={isRunning || titles.length === 0 || !pluginKey}
      >
        <Sparkles className="mr-2 size-4" />
        {isRunning
          ? `Searching ${outcomes.length + 1} of ${titles.length}…`
          : `Add first match for ${titles.length} title${
              titles.length === 1 ? "" : "s"
            }`}
      </Button>
    </div>
  )
}
