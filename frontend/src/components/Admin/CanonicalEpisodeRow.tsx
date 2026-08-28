// TODO: Validate
import type { ReactNode } from "react"

import type { EpisodeRecord } from "@/client"
import { formatDuration } from "@/components/ChannelCommon/formatters"
import { cn } from "@/lib/utils"
import type { NumberingAgreement } from "./tmdbNumbering"

// TODO: Validate
/** "S1E1", or as much of it as the record was numbered with. */
export function numbering(
  seasonNumber: number | null | undefined,
  episodeNumber: number | null | undefined,
): string {
  return `S${seasonNumber ?? "?"}E${episodeNumber ?? "?"}`
}

// TODO: Validate
/**
 * A name that opens its own page on themoviedb.org, where TMDB has one.
 *
 * Which episode a record is comes down to reading it on TMDB, so the names are
 * what open it rather than a link beside them: the whole row is already as much
 * as fits, and a name is what somebody goes to click.
 */
export function TmdbPageLink({
  url,
  children,
}: {
  url: string | null | undefined
  children: ReactNode
}) {
  if (!url) return <>{children}</>
  return (
    <a
      href={url}
      target="_blank"
      rel="noopener noreferrer"
      className="hover:underline"
    >
      {children}
    </a>
  )
}

interface CanonicalEpisodeRowProps {
  record: EpisodeRecord
  /** Left off by a row nothing counted through the title for. */
  absoluteNumber?: number | null
  /** Which of the numbers the episode being settled puts elsewhere. */
  disagreement?: NumberingAgreement
  /** Between the name and the dates, where a choice says who else is on it. */
  middle?: ReactNode
  /** After the dates, where the row's own control goes. */
  trailing?: ReactNode
}

// TODO: Validate
/**
 * One canonical episode, as both the linked list and the choices read it.
 *
 * The two lists are the same question asked twice - which episode is this one -
 * so a row already linked reads exactly as the row that would have linked it,
 * and the numbering, the names and the pages on TMDB sit in the same places in
 * both.
 */
export function CanonicalEpisodeRow({
  record,
  absoluteNumber,
  disagreement,
  middle,
  trailing,
}: CanonicalEpisodeRowProps) {
  return (
    <div className="flex items-center gap-3 border-b px-3 py-2 text-sm last:border-b-0">
      <span className="w-36 shrink-0 tabular-nums">
        <span
          className={
            disagreement?.seasonAndEpisode
              ? "text-destructive"
              : "text-muted-foreground"
          }
        >
          {numbering(
            record.season.season_number,
            record.episode.episode_number,
          )}
        </span>
        {absoluteNumber === undefined ? null : (
          <span
            className={cn(
              "block text-xs",
              disagreement?.absolute
                ? "text-destructive"
                : "text-muted-foreground",
            )}
          >
            {absoluteNumber === null
              ? "No absolute episode"
              : `Absolute Episode #${absoluteNumber}`}
          </span>
        )}
      </span>
      <span className="flex-1 whitespace-normal wrap-break-word">
        <TmdbPageLink url={record.episode.tmdb_url}>
          {record.episode.name ?? "Unnamed"}
        </TmdbPageLink>
        <span className="block text-xs text-muted-foreground">
          <TmdbPageLink url={record.show.tmdb_url}>
            {record.show.name ?? "Unnamed"}
          </TmdbPageLink>
        </span>
      </span>
      {middle}
      <span className="w-20 shrink-0 text-right text-xs tabular-nums text-muted-foreground">
        {record.episode.air_date
          ? new Date(record.episode.air_date).toLocaleDateString()
          : "No air date"}
        <span className="block">
          {formatDuration(record.episode.duration) ?? "No duration"}
        </span>
      </span>
      {trailing}
    </div>
  )
}
