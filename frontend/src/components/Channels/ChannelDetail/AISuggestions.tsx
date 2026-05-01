// TODO: Validate
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { Check, Copy, ExternalLink, Loader2, Sparkles } from "lucide-react"
import { useState } from "react"

import { ChannelsService, type ShowPublic } from "@/client"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import useCustomToast from "@/hooks/useCustomToast"

type Provider = "anthropic" | "openai"

interface ModelOption {
  id: string
  /** Approximate per-1M-token input/output rate. Provider pricing may have
   * shifted — treat as a relative-cost hint, not an authoritative quote. */
  cost: string
}

interface ProviderConfig {
  label: string
  models: ModelOption[]
  apiKeyHint: string
}

const PROVIDERS: Record<Provider, ProviderConfig> = {
  anthropic: {
    label: "Claude (Anthropic)",
    models: [
      { id: "claude-opus-4-7", cost: "$15 / $75 per 1M (most capable)" },
      { id: "claude-opus-4-6", cost: "$15 / $75 per 1M" },
      { id: "claude-sonnet-4-6", cost: "$3 / $15 per 1M (balanced)" },
      { id: "claude-sonnet-4-5", cost: "$3 / $15 per 1M" },
      {
        id: "claude-haiku-4-5-20251001",
        cost: "$1 / $5 per 1M (fast / cheap)",
      },
    ],
    apiKeyHint: "starts with sk-ant-",
  },
  openai: {
    label: "OpenAI",
    models: [
      { id: "gpt-5", cost: "$1.25 / $10 per 1M (flagship)" },
      { id: "gpt-5-mini", cost: "~$0.25 / $2 per 1M" },
      { id: "gpt-4o", cost: "$2.50 / $10 per 1M" },
      { id: "gpt-4o-mini", cost: "$0.15 / $0.60 per 1M (cheapest)" },
      { id: "o3", cost: "$2 / $8 per 1M (reasoning)" },
      { id: "o3-mini", cost: "$1.10 / $4.40 per 1M (reasoning, cheaper)" },
      { id: "o1", cost: "$15 / $60 per 1M (reasoning, premium)" },
      { id: "o1-mini", cost: "$1.10 / $4.40 per 1M (reasoning, cheaper)" },
    ],
    apiKeyHint: "starts with sk-",
  },
}

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
    return (
      host === "youtube.com" ||
      host.endsWith(".youtube.com") ||
      host === "youtu.be" ||
      host === "www.youtu.be"
    )
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

async function enrichWithImages(
  suggestions: Suggestion[],
): Promise<Suggestion[]> {
  const results = await Promise.all(
    suggestions.map(async (s) => {
      // 1. If the AI provided an image_url, try it first (validated via onError in the UI).
      //    We still run the Wikipedia lookup in parallel so we have a fallback ready
      //    if the AI image turns out to be broken at render time — but we only use it
      //    when the AI didn't supply one.
      if (s.image_url) {
        // AI gave us something — trust it and skip the Wikipedia lookup.
        return s
      }

      // 2. Try Wikipedia by exact title.
      let image_url = await fetchWikipediaThumbnail(s.title)

      // 3. If that failed and the url is a Wikipedia link, try the page title from the URL.
      if (!image_url && s.url && isWikipediaUrl(s.url)) {
        const match = s.url.match(/wikipedia\.org\/wiki\/([^#?]+)/)
        if (match) {
          const pageTitle = decodeURIComponent(match[1]).replace(/_/g, " ")
          image_url = await fetchWikipediaThumbnail(pageTitle)
        }

        // Wikipedia URL was provided but we still couldn't get an image —
        // fall back to a Google search so the "More info" link stays useful.
        if (!image_url) {
          const query = [s.title, s.year].filter(Boolean).join(" ")
          s = {
            ...s,
            url: `https://www.google.com/search?q=${encodeURIComponent(query)}`,
          }
        }
      }

      return { ...s, image_url }
    }),
  )
  return results
}

function buildPrompt(showsByType: Record<string, ShowPublic[]>): string {
  const groupedSections = Object.entries(showsByType)
    .map(([type, shows]) => {
      const uniqueNames = Array.from(
        new Set(shows.map((show) => show.name ?? "(untitled)")),
      ).sort((a, b) => a.localeCompare(b))
      const lines = uniqueNames.map((name) => `- ${name}`).join("\n")
      return `## ${type}\n${lines}`
    })
    .join("\n\n")

  return buildPromptBody(groupedSections, "")
}

function buildMorePrompt(
  showsByType: Record<string, ShowPublic[]>,
  alreadySuggested: Suggestion[],
): string {
  const groupedSections = Object.entries(showsByType)
    .map(([type, shows]) => {
      const uniqueNames = Array.from(
        new Set(shows.map((show) => show.name ?? "(untitled)")),
      ).sort((a, b) => a.localeCompare(b))
      const lines = uniqueNames.map((name) => `- ${name}`).join("\n")
      return `## ${type}\n${lines}`
    })
    .join("\n\n")

  const alreadyLines = alreadySuggested
    .map((s) => `- ${s.title}${s.year ? ` (${s.year})` : ""}`)
    .join("\n")

  const exclusionSection = `# Already suggested — do not repeat these\n\n${alreadyLines}`

  return buildPromptBody(groupedSections, exclusionSection)
}

function buildPromptBody(
  groupedSections: string,
  exclusionSection: string,
): string {
  return `You are recommending shows / movies / Youtube channels to add to a media channel based on what is already there.

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

async function callAnthropic(
  apiKey: string,
  model: string,
  prompt: string,
): Promise<string> {
  const response = await fetch("https://api.anthropic.com/v1/messages", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "x-api-key": apiKey,
      "anthropic-version": "2023-06-01",
      "anthropic-dangerous-direct-browser-access": "true",
    },
    body: JSON.stringify({
      model,
      max_tokens: 2048,
      messages: [{ role: "user", content: prompt }],
    }),
  })
  if (!response.ok) {
    const text = await response.text()
    throw new Error(`Anthropic ${response.status}: ${text}`)
  }
  const data = await response.json()
  const block = data?.content?.[0]
  if (!block || block.type !== "text") {
    throw new Error("Unexpected Anthropic response shape")
  }
  return block.text as string
}

async function callOpenAI(
  apiKey: string,
  model: string,
  prompt: string,
): Promise<string> {
  const response = await fetch("https://api.openai.com/v1/chat/completions", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${apiKey}`,
    },
    body: JSON.stringify({
      model,
      messages: [{ role: "user", content: prompt }],
    }),
  })
  if (!response.ok) {
    const text = await response.text()
    throw new Error(`OpenAI ${response.status}: ${text}`)
  }
  const data = await response.json()
  const content = data?.choices?.[0]?.message?.content
  if (typeof content !== "string") {
    throw new Error("Unexpected OpenAI response shape")
  }
  return content
}

function parseSuggestions(raw: string): Suggestion[] {
  const fence = raw.match(/```(?:json)?\s*([\s\S]*?)```/i)
  const jsonText = (fence?.[1] ?? raw).trim()
  const arrayMatch = jsonText.match(/\[[\s\S]*\]/)
  if (!arrayMatch) throw new Error("No JSON array found in response")
  const parsed = JSON.parse(arrayMatch[0])
  if (!Array.isArray(parsed)) throw new Error("Response was not an array")
  return parsed.map((item) => {
    let similarTo: string[] | undefined
    if (Array.isArray(item.similar_to)) {
      similarTo = item.similar_to.map((entry: unknown) => String(entry))
    } else if (typeof item.similar_to === "string" && item.similar_to.trim()) {
      similarTo = [item.similar_to]
    }
    return {
      title: String(item.title ?? "(unknown)"),
      similar_to: similarTo,
      description: item.description ? String(item.description) : undefined,
      year: item.year,
      url: item.url ? String(item.url) : undefined,
      image_url: item.image_url ? String(item.image_url) : undefined,
    }
  })
}

export function AISuggestions({
  channelId,
  onRequestSearch,
}: AISuggestionsProps) {
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const queryClient = useQueryClient()
  const [provider, setProvider] = useState<Provider>("anthropic")
  const [model, setModel] = useState<string>(PROVIDERS.anthropic.models[0].id)
  const [apiKey, setApiKey] = useState<string>("")
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
  const [activeTab, setActiveTab] = useState<"builtin" | "own">("builtin")
  const [addingTitle, setAddingTitle] = useState<string | null>(null)

  const { data: channelShows, isLoading: isLoadingShows } = useQuery({
    queryKey: ["channel-shows-ai", channelId],
    queryFn: () => ChannelsService.getChannelShows({ channelId }),
    refetchOnWindowFocus: false,
  })

  const shows = channelShows?.shows ?? []
  const grouped = shows.length > 0 ? groupShows(shows) : null
  const prompt = grouped ? buildPrompt(grouped) : ""

  const mutation = useMutation({
    mutationFn: async () => {
      if (!apiKey.trim()) throw new Error("Enter an API key first.")
      if (!grouped) throw new Error("This channel has no shows to learn from.")
      const raw =
        provider === "anthropic"
          ? await callAnthropic(apiKey.trim(), model, prompt)
          : await callOpenAI(apiKey.trim(), model, prompt)
      return enrichWithImages(parseSuggestions(raw))
    },
    onSuccess: (data) => {
      setSuggestions((prev) => [...(prev ?? []), ...data])
      showSuccessToast(`Got ${data.length} suggestions`)
    },
    onError: (error: unknown) => {
      const message = error instanceof Error ? error.message : String(error)
      showErrorToast(`AI request failed: ${message}`)
    },
  })

  const moreMutation = useMutation({
    mutationFn: async () => {
      if (!apiKey.trim()) throw new Error("Enter an API key first.")
      if (!grouped) throw new Error("This channel has no shows to learn from.")
      const morePrompt = buildMorePrompt(grouped, suggestions ?? [])
      const raw =
        provider === "anthropic"
          ? await callAnthropic(apiKey.trim(), model, morePrompt)
          : await callOpenAI(apiKey.trim(), model, morePrompt)
      return enrichWithImages(parseSuggestions(raw))
    },
    onSuccess: (data) => {
      setSuggestions((prev) => [...(prev ?? []), ...data])
      showSuccessToast(`Got ${data.length} more suggestions`)
    },
    onError: (error: unknown) => {
      const message = error instanceof Error ? error.message : String(error)
      showErrorToast(`AI request failed: ${message}`)
    },
  })

  const onProviderChange = (next: Provider) => {
    setProvider(next)
    setModel(PROVIDERS[next].models[0].id)
    setApiKey("")
  }

  const onReadFromClipboard = async (text: string) => {
    if (!text.trim()) return
    try {
      const parsed = await enrichWithImages(parseSuggestions(text))
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
      const morePrompt = buildMorePrompt(grouped, suggestions ?? [])
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
        Get show recommendations based on what's already in this channel. Your
        API key is held only while this view is open and is sent directly from
        your browser to the provider — it is never stored or forwarded through
        this server.
      </p>

      <Tabs
        defaultValue="builtin"
        className="w-full"
        onValueChange={(v) => setActiveTab(v as "builtin" | "own")}
      >
        <TabsList className="grid w-full grid-cols-2">
          <TabsTrigger value="builtin">Use built-in client</TabsTrigger>
          <TabsTrigger value="own">Use my own model</TabsTrigger>
        </TabsList>

        <TabsContent value="builtin" className="space-y-4 pt-4">
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1">
              <Label>Provider</Label>
              <Select
                value={provider}
                onValueChange={(value) => onProviderChange(value as Provider)}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {Object.entries(PROVIDERS).map(([key, info]) => (
                    <SelectItem key={key} value={key}>
                      {info.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1">
              <Label>Model</Label>
              <Select value={model} onValueChange={setModel}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {PROVIDERS[provider].models.map((m) => (
                    <SelectItem key={m.id} value={m.id}>
                      <span className="font-mono">{m.id}</span>
                      <span className="ml-2 text-xs text-muted-foreground">
                        {m.cost}
                      </span>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="space-y-1">
            <Label>
              API key{" "}
              <span className="text-muted-foreground text-xs">
                ({PROVIDERS[provider].apiKeyHint}, not stored)
              </span>
            </Label>
            <Input
              type="password"
              autoComplete="off"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder="Required for built-in run"
            />
          </div>

          <Button
            type="button"
            onClick={() => mutation.mutate()}
            disabled={
              mutation.isPending || isLoadingShows || !grouped || !apiKey.trim()
            }
          >
            {mutation.isPending ? "Asking…" : "Run"}
          </Button>
        </TabsContent>

        <TabsContent value="own" className="space-y-4 pt-4">
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
              Copy the prompt, run it in your model of choice, then paste the
              response into the box above.
            </p>
          </div>
        </TabsContent>
      </Tabs>

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
                  {/* Poster */}
                  <div className="relative aspect-[2/3] bg-muted shrink-0">
                    {suggestion.image_url ? (
                      <img
                        src={suggestion.image_url}
                        alt={suggestion.title}
                        onError={async (e) => {
                          const img = e.currentTarget
                          // AI-supplied URL broke — try Wikipedia API as fallback
                          const wikiUrl = await fetchWikipediaThumbnail(
                            suggestion.title,
                          )
                          if (wikiUrl) {
                            img.src = wikiUrl
                            return
                          }
                          // Nothing worked — show text fallback
                          img.style.display = "none"
                          const fallback =
                            img.nextElementSibling as HTMLElement | null
                          if (fallback) fallback.style.display = "flex"
                        }}
                        className="w-full h-full object-cover"
                      />
                    ) : null}
                    {/* Text-only fallback — always rendered, hidden when image loads */}
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

                  {/* Content */}
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
          {activeTab === "builtin" && apiKey.trim() ? (
            <div className="flex justify-center pt-2">
              <Button
                type="button"
                variant="outline"
                onClick={() => moreMutation.mutate()}
                disabled={moreMutation.isPending || mutation.isPending}
              >
                {moreMutation.isPending ? (
                  <>
                    <Loader2 className="mr-2 size-4 animate-spin" /> Getting
                    more…
                  </>
                ) : (
                  <>
                    <Sparkles className="mr-2 size-4" /> More results
                  </>
                )}
              </Button>
            </div>
          ) : activeTab === "own" ? (
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
          ) : null}
        </div>
      )}
    </div>
  )
}
