// TODO: Validate
import type { ReactNode } from "react"

import type { EpisodeListOutput, EpisodeRecord } from "@/client"
import { ResultCard } from "@/components/Channels/ChannelDetail/Search"
import { useOpenMedia } from "@/hooks/useOpenMedia"
import type { EditableEpisodeFields } from "./Edit"

export interface LinkedEpisodeEntry {
  record: Pick<EditableEpisodeFields, "id"> & Partial<EditableEpisodeFields>
  name: string | null
  episodeNumber: number | null
  imageUrl: string | null
  url: string | null
  seasonName: string | null
  seasonNumber: number | null
  titleName: string | null
  sourceKey: string
  faviconUrl: string | null
  seasonId: string
  titleId: string
  sourceId: string
  pluginId: string
}

// TODO: Validate
export function entryFromEpisodeList(
  episode: EpisodeListOutput,
): LinkedEpisodeEntry {
  return {
    record: episode,
    name: episode.name ?? null,
    episodeNumber: episode.episode_number ?? null,
    imageUrl: episode.thumbnail_url ?? episode.image_url ?? null,
    url: episode.url ?? null,
    seasonName: episode.season_name,
    seasonNumber: episode.season_number,
    titleName: episode.title_name,
    sourceKey: episode.source_key,
    faviconUrl: episode.source_favicon_url,
    seasonId: episode.season_id,
    titleId: episode.title_id,
    sourceId: episode.source_id,
    pluginId: episode.plugin_id,
  }
}

// TODO: Validate
export function entryFromEpisodeRecord(
  record: EpisodeRecord,
): LinkedEpisodeEntry {
  return {
    record: record.episode,
    name: record.episode.name ?? null,
    episodeNumber: record.episode.episode_number ?? null,
    imageUrl: record.episode.thumbnail_url ?? record.episode.image_url ?? null,
    url: record.episode.tmdb_url ?? record.episode.url ?? null,
    seasonName: record.season.name ?? null,
    seasonNumber: record.season.season_number ?? null,
    titleName: record.title.name ?? null,
    sourceKey: record.source.key,
    faviconUrl: record.source.favicon_url ?? null,
    seasonId: record.episode.season_id,
    titleId: record.season.title_id,
    sourceId: record.title.source_id,
    pluginId: record.source.plugin_id,
  }
}

// TODO: Validate
export function seasonText(entry: LinkedEpisodeEntry) {
  const numbered =
    entry.seasonNumber == null ? null : `Season ${entry.seasonNumber}`
  if (!entry.seasonName) return numbered
  if (!numbered) return entry.seasonName
  return `${entry.seasonName} (${numbered})`
}

// TODO: Validate
function episodeCardTitle(entry: LinkedEpisodeEntry) {
  const name = entry.name || "Untitled"
  if (entry.episodeNumber == null) {
    return name
  }
  return `${entry.episodeNumber}. ${name}`
}

interface LinkedEpisodeCardsProps {
  entries: LinkedEpisodeEntry[]
  /** The control that takes a link off, which is an admin's alone. */
  renderUnlink?: (entry: LinkedEpisodeEntry) => ReactNode
  /**
   * Whether a card names the website it came from, which is worth reading where
   * the episodes come from several and says nothing where they all come from one.
   */
  showSource?: boolean
}

// TODO: Validate
export function LinkedEpisodeCards({
  entries,
  renderUnlink,
  showSource = true,
}: LinkedEpisodeCardsProps) {
  const openMedia = useOpenMedia()

  return (
    <div className="flex flex-wrap gap-3">
      {entries.map((entry) => (
        <ResultCard
          key={entry.record.id}
          imageUrl={entry.imageUrl}
          title={episodeCardTitle(entry)}
          subtitle={
            <>
              {showSource ? <span>{entry.sourceKey}</span> : null}
              {seasonText(entry) ? (
                <span className="block">{seasonText(entry)}</span>
              ) : null}
              {entry.titleName ? (
                <span className="block">{entry.titleName}</span>
              ) : null}
            </>
          }
          onClick={() => openMedia({ kind: "episode", episode: entry.record })}
          footer={renderUnlink?.(entry)}
        />
      ))}
    </div>
  )
}
