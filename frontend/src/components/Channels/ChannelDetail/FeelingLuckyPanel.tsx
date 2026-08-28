// TODO: Validate
import { useQueryClient } from "@tanstack/react-query"
import { Check, Sparkles, X } from "lucide-react"
import { useState } from "react"

import {
  ChannelsService,
  type PluginSearchResult,
  PluginsService,
} from "@/client"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"
import { MediaInfoModal, PluginResultCard, type SelectedTitle } from "./Search"

/** What became of one title the search was run for. */
interface LuckyOutcome {
  title: string
  /** The first result the search returned, or null when it returned none. */
  result: PluginSearchResult | null
  failed: boolean
  /** Whether this one is to be queued when the list is saved. */
  approved: boolean
}

// TMDB covers every service rather than one, so a title is looked for there and
// nowhere else. Feeling lucky is taking the first result of a search on trust,
// and a catalogue of everything is the only one where the first result standing
// for the title is a fair bet - one service's search answers only for what that
// service carries, so its first result is whatever it holds that reads closest.
const PLUGIN_KEY = "TMDB"

// TODO: Validate
function parseTitles(text: string): string[] {
  return text
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean)
}

// TODO: Validate
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
 * be opened to see what its own plugin has on it before deciding.
 */
export function FeelingLuckyPanel({ channelId }: { channelId: string }) {
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const [titlesText, setTitlesText] = useState("")
  const [outcomes, setOutcomes] = useState<LuckyOutcome[]>([])
  const [isRunning, setIsRunning] = useState(false)
  const [isSaving, setIsSaving] = useState(false)
  const [openedTitle, setOpenedTitle] = useState<SelectedTitle | null>(null)

  const titles = parseTitles(titlesText)
  const matched = outcomes.filter((outcome) => outcome.result !== null)
  const unmatched = outcomes.filter((outcome) => outcome.result === null)
  const approved = matched.filter((outcome) => outcome.approved)

  // A result already says which plugin issued it and under what id, so opening a
  // title names it outright instead of searching another service for it. A
  // result the plugin gave no id for is one nothing can be asked about.
  // TODO: Validate
  const openTitle = (result: PluginSearchResult) => {
    if (!result.media_identifier) {
      showErrorToast(`No details found for “${result.title}”`)
      return
    }
    setOpenedTitle({
      plugin_key: PLUGIN_KEY,
      media_identifier: result.media_identifier,
      title: result.title,
      url: result.url,
      year: result.year,
      image_url: result.image_url,
    })
  }

  // TODO: Validate
  const setApproval = (title: string, isApproved: boolean) => {
    setOutcomes((current) =>
      current.map((outcome) =>
        outcome.title === title
          ? { ...outcome, approved: isApproved }
          : outcome,
      ),
    )
  }

  // TODO: Validate
  const setEveryApproval = (isApproved: boolean) => {
    setOutcomes((current) =>
      current.map((outcome) => ({ ...outcome, approved: isApproved })),
    )
  }

  // TODO: Validate
  const run = async () => {
    setIsRunning(true)
    setOutcomes([])

    const found: LuckyOutcome[] = []
    // Searched one at a time so a plugin is not asked for every title at once,
    // and so the list fills in as it goes rather than all at the end.
    for (const title of titles) {
      try {
        const page = await PluginsService.inAppSearch({
          pluginKey: PLUGIN_KEY,
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

  // TODO: Validate
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
        One title per line. Each is searched and its first result is shown as a
        card, and the ones left on Importing are added to the import queue.
      </p>

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
                Import all
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setEveryApproval(false)}
              >
                Skip all
              </Button>
            </div>
          )}

          <div className="max-h-96 overflow-y-auto rounded-lg border p-2">
            <div className="flex flex-wrap gap-3">
              {matched.map((outcome) => (
                <div key={outcome.title} className="flex flex-col gap-1">
                  <span className="max-w-36 truncate text-xs text-muted-foreground">
                    {outcome.title}
                  </span>
                  <PluginResultCard
                    result={outcome.result!}
                    channelId={channelId}
                    onSelect={openTitle}
                    extraFooter={
                      <Button
                        size="sm"
                        variant={outcome.approved ? "secondary" : "outline"}
                        className="mt-2 w-full"
                        onClick={() =>
                          setApproval(outcome.title, !outcome.approved)
                        }
                      >
                        {outcome.approved ? (
                          <Check className="h-3 w-3 mr-1" />
                        ) : (
                          <X className="h-3 w-3 mr-1" />
                        )}
                        {outcome.approved ? "Importing" : "Skipped"}
                      </Button>
                    }
                  />
                </div>
              ))}
            </div>

            {unmatched.length > 0 && (
              <div className="mt-2 space-y-1 text-sm">
                {unmatched.map((outcome) => (
                  <div key={outcome.title} className="flex items-start gap-2">
                    <X className="mt-0.5 size-4 shrink-0 text-destructive" />
                    <span className="min-w-0 whitespace-normal wrap-break-word">
                      <span className="font-medium">{outcome.title}</span>
                      <span className="text-muted-foreground">
                        {outcome.failed ? " — search failed" : " — no results"}
                      </span>
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      <div className="flex flex-wrap items-center gap-2">
        <Button
          onClick={run}
          disabled={isRunning || isSaving || titles.length === 0}
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
