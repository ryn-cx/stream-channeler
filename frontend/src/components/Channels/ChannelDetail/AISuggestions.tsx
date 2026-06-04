// TODO: Validate
import { useQuery, useQueryClient } from "@tanstack/react-query"
import { Check, Copy, ExternalLink, Loader2, Sparkles } from "lucide-react"
import { useState } from "react"

import { ChannelsService, type ShowPublic } from "@/client"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import useCustomToast from "@/hooks/useCustomToast"

interface Suggestion {
  title: string
  similar_to?: string[]
  description?: string
  year?: number | string
  url?: string
  image_url?: string
}

interface AISuggestionsProps {
  channelId: string
  onRequestSearch?: (title: string) => void
}

function isYouTubeUrl(url: string): boolean {
  try {
    const parsed = new URL(url)
    const host = parsed.hostname.toLowerCase()
    return host.endsWith("youtube.com") || host.endsWith("youtu.be")
  } catch {
    return false
  }
}

function isWikipediaUrl(url: string): boolean {
  try {
    return new URL(url).hostname.endsWith("wikipedia.org")
  } catch {
    return false
  }
}

async function fetchWikipediaThumbnail(
  title: string,
): Promise<string | undefined> {
  try {
    const encoded = encodeURIComponent(title)
    const res = await fetch(
      `https://en.wikipedia.org/api/rest_v1/page/summary/${encoded}`,
    )
    if (!res.ok) return undefined
    const data = await res.json()
    return (data?.thumbnail?.source as string | undefined) ?? undefined
  } catch {
    return undefined
  }
}

async function findMissingImages(
  suggestions: Suggestion[],
): Promise<Suggestion[]> {
  const results = await Promise.all(
    suggestions.map(async (s) => {
      if (s.image_url) {
        return s
      }

      let image_url: string | undefined
      if (s.url && isWikipediaUrl(s.url)) {
        const match = s.url.match(/wikipedia\.org\/wiki\/([^#?]+)/)
        if (match) {
          const pageTitle = decodeURIComponent(match[1]).replace(/_/g, " ")
          image_url = await fetchWikipediaThumbnail(pageTitle)
        }
      }

      return { ...s, image_url }
    }),
  )
  return results
}

function buildGroupedSections(
  showsByType: Record<string, ShowPublic[]>,
): string {
  return Object.entries(showsByType)
    .map(([type, shows]) => {
      const uniqueNames = Array.from(
        new Set(
          shows
            .map((show) => show.name)
            .filter((name): name is string => Boolean(name)),
        ),
      ).sort((a, b) => a.localeCompare(b))
      // Skip a whole section if every show in it was untitled.
      if (uniqueNames.length === 0) return null
      const lines = uniqueNames.map((name) => `- ${name}`).join("\n")
      return `## ${type}\n${lines}`
    })
    .filter(Boolean)
    .join("\n\n")
}

function buildPrompt(
  showsByType: Record<string, ShowPublic[]>,
  alreadySuggested: Suggestion[] = [],
): string {
  const groupedSections = buildGroupedSections(showsByType)

  // Describe the channel using the media types it actually contains — only the
  // types that have at least one titled show, matching the sections below.
  const mediaTypes = Object.entries(showsByType)
    .filter(([, shows]) => shows.some((show) => Boolean(show.name)))
    .map(([type]) => type)
  const mediaTypesPhrase =
    mediaTypes.length > 0 ? mediaTypes.join(" / ") : "content"

  const exclusionSection =
    alreadySuggested.length > 0
      ? `# Already suggested — do not repeat these\n\n${alreadySuggested
          .map((s) => `- ${s.title}${s.year ? ` (${s.year})` : ""}`)
          .join("\n")}`
      : ""

  return `You are recommending ${mediaTypesPhrase} to add to a media channel based on what is already there.

The user already follows the items below, grouped by type. Suggest 10 new items that are similar in theme, tone, or genre. Do not repeat anything from the existing list. There should be at least one type of suggestion for each of the different types in the existing list.

Respond with a JSON array of objects only. No prose before or after. Each object must have:
  - "title": string (the name of the show / movie / channel)
  - "year": number (release year if known, otherwise omit)
  - "similar_to": array of strings (1 to 10 entries) (names taken from the existing list above — list as many as genuinely apply)
  - "description": string (one or two sentences describing what the suggestion itself is, so the user knows what it is)
  - "url": string (see URL rules below)
  - "image_url": string (optional, see image URL rules below)

URL rules:
  - If the suggestion is a YouTube channel, return its real YouTube channel URL (e.g. https://www.youtube.com/@handle or https://www.youtube.com/channel/UCxxxx). This URL will be used directly to add the channel.
  - For anything else (TV show, movie, anime, etc.), prefer the Wikipedia article URL (e.g. https://en.wikipedia.org/wiki/Title). Only use another source (IMDb, official site) if you are confident there is no Wikipedia article for it.

Image URL rules:
  - Provide the direct Wikipedia thumbnail URL for the article's main image if you know it, e.g. https://upload.wikimedia.org/wikipedia/en/thumb/.../220px-....jpg
  - For YouTube channels provide the channel avatar URL if known.
  - If you are not confident the image URL is real and publicly accessible, omit the field — the app will fall back to the Wikipedia API automatically.

Example:
[
  {
    "title": "{TITLE}",
    "year": {YEAR},
    "similar_to": ["{EXISTING SHOW 1}", "{EXISTING SHOW 2}", "{EXISTING SHOW 3}", "{EXISTING SHOW 4}", "{EXISTING SHOW 5}", "{EXISTING SHOW 6}", "{EXISTING SHOW 7}", "{EXISTING SHOW 8}", "{EXISTING SHOW 9}", "{EXISTING SHOW 10}"],
    "description": "{ONE OR TWO SENTENCES DESCRIBING THE SUGGESTION ITSELF}",
    "url": "{WIKIPEDIA OR YOUTUBE URL}",
    "image_url": "{DIRECT IMAGE URL IF CONFIDENT, OTHERWISE OMIT}"
  }
]
${exclusionSection ? `\n${exclusionSection}\n` : ""}
# Existing items

${groupedSections}
`
}

function groupShows(shows: ShowPublic[]): Record<string, ShowPublic[]> {
  const groups: Record<string, ShowPublic[]> = {}
  for (const show of shows) {
    const key = show.media_type || "Other"
    if (!groups[key]) groups[key] = []
    groups[key].push(show)
  }
  return groups
}

function parseSuggestions(raw: string): Suggestion[] {
  const parsed = JSON.parse(raw.trim())
  if (!Array.isArray(parsed)) throw new Error("Response was not an array")
  return parsed as Suggestion[]
}

export function AISuggestions({
  channelId,
  onRequestSearch,
}: AISuggestionsProps) {
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const queryClient = useQueryClient()
  const storageKey = `ai-suggestions-${channelId}`

  const [suggestions, setSuggestionsRaw] = useState<Suggestion[] | null>(() => {
    try {
      const stored = localStorage.getItem(storageKey)
      return stored ? (JSON.parse(stored) as Suggestion[]) : null
    } catch {
      return null
    }
  })

  const setSuggestions = (
    updater:
      | Suggestion[]
      | null
      | ((prev: Suggestion[] | null) => Suggestion[] | null),
  ) => {
    setSuggestionsRaw((prev) => {
      const next = typeof updater === "function" ? updater(prev) : updater
      try {
        if (next) localStorage.setItem(storageKey, JSON.stringify(next))
        else localStorage.removeItem(storageKey)
      } catch {
        // storage quota exceeded or unavailable — ignore
      }
      return next
    })
  }
  const [copied, setCopied] = useState(false)
  const [copiedMore, setCopiedMore] = useState(false)
  const [addingTitle, setAddingTitle] = useState<string | null>(null)

  const { data: channelShows, isLoading: isLoadingShows } = useQuery({
    queryKey: ["channel-shows-ai", channelId],
    queryFn: () => ChannelsService.getChannelShows({ channelId }),
    refetchOnWindowFocus: false,
  })

  const shows = channelShows?.shows ?? []
  const grouped = shows.length > 0 ? groupShows(shows) : null
  const prompt = grouped ? buildPrompt(grouped) : ""

  const onReadFromClipboard = async (text: string) => {
    if (!text.trim()) return
    try {
      const parsed = await findMissingImages(parseSuggestions(text))
      setSuggestions((prev) => [...(prev ?? []), ...parsed])
      showSuccessToast(`Parsed ${parsed.length} suggestions`)
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error)
      showErrorToast(`Could not parse response: ${message}`)
    }
  }

  const onCopyMorePrompt = async () => {
    if (!grouped) return
    try {
      const morePrompt = buildPrompt(grouped, suggestions ?? [])
      await navigator.clipboard.writeText(morePrompt)
      setCopiedMore(true)
      setTimeout(() => setCopiedMore(false), 1500)
      showSuccessToast("More prompt copied to clipboard")
    } catch (error) {
      showErrorToast(`Could not copy: ${error}`)
    }
  }

  const onCopyPrompt = async () => {
    try {
      await navigator.clipboard.writeText(prompt)
      setCopied(true)
      setTimeout(() => setCopied(false), 1500)
      showSuccessToast("Prompt copied to clipboard")
    } catch (error) {
      showErrorToast(`Could not copy: ${error}`)
    }
  }

  const addUrlToChannel = async (url: string, label: string) => {
    setAddingTitle(label)
    try {
      await ChannelsService.createChannelQueueUrls({
        channelId,
        requestBody: [url],
      })
      await queryClient.invalidateQueries({
        queryKey: ["channelQueue", channelId],
      })
      showSuccessToast(`Added "${label}" to import queue`)
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error)
      showErrorToast(`Could not add: ${message}`)
    } finally {
      setAddingTitle(null)
    }
  }

  const onSuggestionClick = async (suggestion: Suggestion) => {
    if (suggestion.url && isYouTubeUrl(suggestion.url)) {
      await addUrlToChannel(suggestion.url, suggestion.title)
      return
    }
    onRequestSearch?.(suggestion.title)
  }

  return (
    <div className="space-y-4">
      <p className="text-sm text-muted-foreground">
        Get show recommendations based on what's already in this channel. Copy
        the prompt below, run it in whatever AI you like, then paste the JSON
        response back to see the suggestions. Nothing is sent through this
        server.
      </p>

      <div className="flex items-center gap-2">
        <Button
          type="button"
          variant="outline"
          onClick={onCopyPrompt}
          disabled={!grouped}
        >
          {copied ? (
            <>
              <Check className="mr-2 size-4" /> Copied
            </>
          ) : (
            <>
              <Copy className="mr-2 size-4" /> Copy prompt
            </>
          )}
        </Button>
      </div>

      <div className="space-y-1">
        <Label className="text-sm">Paste response</Label>
        <Input
          placeholder="Paste the model's JSON response here…"
          onPaste={(e) => {
            const text = e.clipboardData.getData("text")
            onReadFromClipboard(text)
          }}
          onChange={() => {
            /* controlled via onPaste */
          }}
          value=""
          className="font-mono text-xs"
        />
        <p className="text-xs text-muted-foreground">
          Copy the prompt, run it in your AI of choice, then paste the response
          into the box above.
        </p>
      </div>

      {!grouped && !isLoadingShows && (
        <p className="text-sm text-muted-foreground">
          This channel has no shows yet — add some before asking for
          suggestions.
        </p>
      )}

      {suggestions && suggestions.length > 0 && (
        <div className="space-y-2">
          <Label className="text-sm">Suggestions</Label>
          <p className="text-xs text-muted-foreground">
            Click a card to add it. YouTube links add directly; everything else
            jumps to the Search tab so you can find the real URL.
          </p>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
            {" "}
            {suggestions.map((suggestion, index) => {
              const isYouTube = suggestion.url
                ? isYouTubeUrl(suggestion.url)
                : false
              const isAdding = addingTitle === suggestion.title
              return (
                // biome-ignore lint/a11y/useSemanticElements: card contains a nested <a> link, so it cannot be a <button>
                <div
                  key={`${suggestion.title}-${index}`}
                  onClick={() => !isAdding && onSuggestionClick(suggestion)}
                  onKeyDown={(e) =>
                    e.key === "Enter" &&
                    !isAdding &&
                    onSuggestionClick(suggestion)
                  }
                  role="button"
                  tabIndex={0}
                  aria-disabled={isAdding}
                  className="flex flex-col border rounded overflow-hidden cursor-pointer hover:border-primary hover:bg-accent/40 transition-colors aria-disabled:opacity-60 aria-disabled:pointer-events-none"
                >
                  <div className="relative aspect-[2/3] bg-muted shrink-0">
                    {suggestion.image_url ? (
                      <img
                        src={suggestion.image_url}
                        alt={suggestion.title}
                        onError={(e) => {
                          const img = e.currentTarget
                          img.style.display = "none"
                          const fallback =
                            img.nextElementSibling as HTMLElement | null
                          if (fallback) fallback.style.display = "flex"
                        }}
                        className="w-full h-full object-cover"
                      />
                    ) : null}
                    <div
                      className="absolute inset-0 flex flex-col items-center justify-center p-2 bg-muted text-center"
                      style={{
                        display: suggestion.image_url ? "none" : "flex",
                      }}
                    >
                      <span className="text-3xl font-bold text-muted-foreground select-none">
                        {suggestion.title.charAt(0).toUpperCase()}
                      </span>
                      <span className="mt-1 text-xs font-medium leading-tight line-clamp-3">
                        {suggestion.title}
                      </span>
                    </div>
                  </div>

                  <div className="p-2 flex flex-col gap-1 flex-1">
                    <div className="flex items-start justify-between gap-1">
                      <div className="min-w-0">
                        <span className="font-medium text-sm leading-tight block">
                          {suggestion.title}
                        </span>
                        {suggestion.year ? (
                          <span className="text-xs text-muted-foreground">
                            {suggestion.year}
                          </span>
                        ) : null}
                      </div>
                      {suggestion.url && (
                        <a
                          href={suggestion.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          onClick={(e) => e.stopPropagation()}
                          title="More info"
                          className="shrink-0 text-muted-foreground hover:text-foreground"
                        >
                          <ExternalLink className="size-3.5" />
                        </a>
                      )}
                    </div>

                    {suggestion.description ? (
                      <p className="text-xs text-muted-foreground line-clamp-3">
                        {suggestion.description}
                      </p>
                    ) : null}

                    {suggestion.similar_to &&
                    suggestion.similar_to.length > 0 ? (
                      <p className="text-xs text-muted-foreground line-clamp-2">
                        <span className="font-medium">Like:</span>{" "}
                        {suggestion.similar_to.join(", ")}
                      </p>
                    ) : null}

                    <div className="flex items-center gap-1 mt-auto pt-1 text-xs text-muted-foreground">
                      {isAdding ? (
                        <Loader2 className="size-3 animate-spin" />
                      ) : isYouTube ? (
                        <ExternalLink className="size-3" />
                      ) : (
                        <Sparkles className="size-3" />
                      )}
                      <span>
                        {isAdding
                          ? "Adding…"
                          : isYouTube
                            ? "Add directly"
                            : "Search"}
                      </span>
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
          <div className="flex justify-center pt-2">
            <Button
              type="button"
              variant="outline"
              onClick={onCopyMorePrompt}
              disabled={!grouped}
            >
              {copiedMore ? (
                <>
                  <Check className="mr-2 size-4" /> Copied
                </>
              ) : (
                <>
                  <Copy className="mr-2 size-4" /> Copy "more results" prompt
                </>
              )}
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}
