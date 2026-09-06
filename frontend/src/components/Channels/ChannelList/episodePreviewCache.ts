// TODO: Validate
import type {
  ChannelOutput,
  ChannelsGetChannelEpisodesResponse,
} from "@/client"

type Preview = ChannelsGetChannelEpisodesResponse

// TODO: Validate
function looksLikePreview(value: unknown): value is Preview {
  if (typeof value !== "object" || value === null) return false
  const preview = value as Partial<Preview>
  return (
    Array.isArray(preview.episodes) &&
    typeof preview.seasons === "object" &&
    typeof preview.titles === "object" &&
    typeof preview.sources === "object" &&
    typeof preview.plugins === "object"
  )
}

// TODO: Validate
function pick<T>(
  source: Record<string, T>,
  ids: Iterable<string | null | undefined>,
): Record<string, T> {
  const kept: Record<string, T> = {}
  for (const id of ids) {
    if (id != null && source[id] !== undefined) kept[id] = source[id]
  }
  return kept
}

// TODO: Validate
function trimmed(preview: Preview): Preview {
  const episodes = preview.episodes.slice(0, 30)
  const seasons = pick(
    preview.seasons,
    episodes.map((episode) => episode.season_id),
  )
  const titles = pick(
    preview.titles,
    Object.values(seasons).map((season) => season.title_id),
  )
  const sources = pick(
    preview.sources,
    Object.values(titles).map((title) => title.source_id),
  )
  return {
    episodes,
    seasons,
    titles,
    sources,
    plugins: pick(
      preview.plugins,
      Object.values(sources).map((source) => source.plugin_id),
    ),
  }
}

// TODO: Validate
export function readEpisodePreview(channelId: string): Preview | undefined {
  const stored = localStorage.getItem(`channel-episodes:${channelId}`)
  if (stored === null) return undefined
  try {
    const parsed: unknown = JSON.parse(stored)
    if (looksLikePreview(parsed)) return parsed
  } catch {
    localStorage.removeItem(`channel-episodes:${channelId}`)
  }
  return undefined
}

// TODO: Validate
export function writeEpisodePreview(channelId: string, preview: Preview): void {
  try {
    localStorage.setItem(
      `channel-episodes:${channelId}`,
      JSON.stringify(trimmed(preview)),
    )
  } catch {
    localStorage.removeItem(`channel-episodes:${channelId}`)
  }
}

// TODO: Validate
export function readChannelDetails(
  channelId: string,
): ChannelOutput | undefined {
  const stored = localStorage.getItem(`channel-details:${channelId}`)
  if (stored === null) return undefined
  try {
    const parsed = JSON.parse(stored) as Partial<ChannelOutput>
    if (typeof parsed.id === "string") return parsed as ChannelOutput
  } catch {
    localStorage.removeItem(`channel-details:${channelId}`)
  }
  return undefined
}

// TODO: Validate
export function writeChannelDetails(channel: ChannelOutput): void {
  try {
    localStorage.setItem(
      `channel-details:${channel.id}`,
      JSON.stringify(channel),
    )
  } catch {
    localStorage.removeItem(`channel-details:${channel.id}`)
  }
}
