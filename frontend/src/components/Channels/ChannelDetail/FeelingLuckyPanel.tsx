// TODO: Validate
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { Sparkles, X } from "lucide-react"
import { useEffect, useState } from "react"

import {
  ChannelsService,
  type PluginSearchResult,
  PluginsService,
} from "@/client"
import { SourceOptionLabel } from "@/components/Common/SourceOptionLabel"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
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
import { MediaInfoModal, type SelectedTitle } from "./Search"

/** What became of one title the search was run for. */
interface LuckyOutcome {
  title: string
  /** The first result the search returned, or null when it returned none. */
  result: PluginSearchResult | null
  failed: boolean
  /** Whether this one is to be queued when the list is saved. */
  approved: boolean
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
 * Search for several titles at once and queue the ones that were matched right.
 *
 * One title per line, since a title can have a comma in it but not a line
 * break. Each is searched on its own so one title finding nothing does not stop
 * the rest.
 *
 * Taking the first result of a search is a guess, and a guess is worth looking
 * at before it becomes a channel's media, so nothing is queued until the list
 * has been gone through. Every match starts approved, which makes the work
 * unticking the wrong ones rather than ticking every right one, and a title can
 * be opened to see what TMDB has on it before deciding.
 */
export function FeelingLuckyPanel({ channelId }: { channelId: string }) {
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const [titlesText, setTitlesText] = useState("")
  const [outcomes, setOutcomes] = useState<LuckyOutcome[]>([])
  const [isRunning, setIsRunning] = useState(false)
  const [isSaving, setIsSaving] = useState(false)
  const [pluginKey, setPluginKey] = useState("")
  const [openedTitle, setOpenedTitle] = useState<SelectedTitle | null>(null)

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
  const matched = outcomes.filter((outcome) => outcome.result !== null)
  const approved = matched.filter((outcome) => outcome.approved)

  // A result carries no TMDB id, so the matching title is looked up when one is
  // opened rather than for every result of every search.
  const openMutation = useMutation({
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
      setOpenedTitle({
        tmdb_id: match.tmdb_id,
        media_type: match.media_type,
        title: result.title,
        url: result.url,
        year: result.year,
        image_url: result.image_url,
      })
    },
    onError: (error) =>
      handleError.call(
        showErrorToast,
        error as Parameters<typeof handleError>[0],
      ),
  })

  const setApproval = (title: string, isApproved: boolean) => {
    setOutcomes((current) =>
      current.map((outcome) =>
        outcome.title === title
          ? { ...outcome, approved: isApproved }
          : outcome,
      ),
    )
  }

  const setEveryApproval = (isApproved: boolean) => {
    setOutcomes((current) =>
      current.map((outcome) => ({ ...outcome, approved: isApproved })),
    )
  }

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
        const first = page.results[0] ?? null
        found.push({ title, result: first, failed: false, approved: true })
      } catch {
        found.push({ title, result: null, failed: true, approved: false })
      }
      setOutcomes([...found])
    }

    setIsRunning(false)
    if (found.every((outcome) => outcome.result === null)) {
      showErrorToast("Nothing was found for any of those titles")
    }
  }

  const save = async () => {
    const urls = approved
      .map((outcome) => outcome.result?.url)
      .filter((url): url is string => Boolean(url))
    if (urls.length === 0) return

    setIsSaving(true)
    try {
      await ChannelsService.createChannelQueueUrls({
        channelId,
        requestBody: urls,
      })
      queryClient.invalidateQueries({ queryKey: ["channelQueue", channelId] })
      showSuccessToast(`Added ${urls.length} to the import queue`)
      setOutcomes([])
    } catch (error) {
      handleError.call(
        showErrorToast,
        error as Parameters<typeof handleError>[0],
      )
    }
    setIsSaving(false)
  }

  return (
    <div className="border rounded-lg p-4 space-y-3">
      <p className="text-sm text-muted-foreground">
        One title per line. Each is searched and its first result is offered for
        approval, and the ones left ticked are added to the import queue.
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
        placeholder={"Show Name 1\nShow Name 2\nShow Name 3"}
        rows={6}
        aria-label="Titles to search"
        disabled={isRunning}
      />

      {outcomes.length > 0 && (
        <div className="space-y-2">
          {matched.length > 0 && (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <span>
                {approved.length} of {matched.length} to add
              </span>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setEveryApproval(true)}
              >
                Tick all
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setEveryApproval(false)}
              >
                Untick all
              </Button>
            </div>
          )}

          <div className="max-h-64 space-y-1 overflow-y-auto rounded-lg border p-2 text-sm">
            {outcomes.map((outcome) => (
              <div key={outcome.title} className="flex items-start gap-2">
                {outcome.result ? (
                  <Checkbox
                    className="mt-0.5 shrink-0"
                    checked={outcome.approved}
                    onCheckedChange={(checked) =>
                      setApproval(outcome.title, checked === true)
                    }
                    aria-label={`Add ${outcome.title}`}
                  />
                ) : (
                  <X className="mt-0.5 size-4 shrink-0 text-destructive" />
                )}
                <span className="min-w-0 whitespace-normal wrap-break-word">
                  <span className="font-medium">{outcome.title}</span>
                  {outcome.result ? (
                    <>
                      <span className="text-muted-foreground">{" → "}</span>
                      <button
                        type="button"
                        className="underline"
                        disabled={openMutation.isPending}
                        onClick={() =>
                          outcome.result && openMutation.mutate(outcome.result)
                        }
                      >
                        {outcome.result.title}
                      </button>
                    </>
                  ) : (
                    <span className="text-muted-foreground">
                      {outcome.failed ? " — search failed" : " — no results"}
                    </span>
                  )}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="flex flex-wrap items-center gap-2">
        <Button
          onClick={run}
          disabled={isRunning || isSaving || titles.length === 0 || !pluginKey}
        >
          <Sparkles className="mr-2 size-4" />
          {isRunning
            ? `Searching ${outcomes.length + 1} of ${titles.length}…`
            : `Search ${titles.length} title${titles.length === 1 ? "" : "s"}`}
        </Button>
        {matched.length > 0 && (
          <Button
            variant="secondary"
            onClick={save}
            disabled={isRunning || isSaving || approved.length === 0}
          >
            {isSaving ? "Saving…" : `Add ${approved.length} to the queue`}
          </Button>
        )}
      </div>

      <MediaInfoModal
        result={openedTitle}
        channelId={channelId}
        onOpenChange={(open) => {
          if (!open) setOpenedTitle(null)
        }}
      />
    </div>
  )
}
