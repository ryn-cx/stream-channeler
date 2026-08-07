// TODO: Validate
import type { ColumnDef } from "@tanstack/react-table"
import type { ReactNode } from "react"

import type { UnmatchedEpisodeOutput } from "@/client"
import { TmdbLink } from "@/components/ChannelCommon/TmdbLink"
import { cn } from "@/lib/utils"
import { TmdbMatchApproval } from "./TmdbMatchApproval"

/**
 * A cell whose text runs onto another line rather than widening the table.
 *
 * A table cell holds its text on one line, which is what pushes a table of
 * names past the width of the window. A cell given a width to stay under wraps
 * inside it instead, and a name too long to break at a space is broken anyway.
 */
function WrappingCell({
  className,
  children,
}: {
  className?: string
  children: ReactNode
}) {
  return (
    <span className={cn("block whitespace-normal wrap-break-word", className)}>
      {children}
    </span>
  )
}

/** "S2E5", or as much of it as the record was numbered with. */
function seasonAndEpisodeText(
  seasonNumber: number | null,
  episodeNumber: number | null,
): string {
  if (seasonNumber === null && episodeNumber === null) return ""
  return `S${seasonNumber ?? "?"}E${episodeNumber ?? "?"}`
}

/** Whether the website and TMDB file the episode under the same season and number. */
function seasonAndEpisodeAgree(episode: UnmatchedEpisodeOutput): boolean {
  const match = episode.best_match
  if (!match) return false
  return (
    episode.season_number !== null &&
    episode.episode_number !== null &&
    episode.season_number === match.season_number &&
    episode.episode_number === match.episode_number
  )
}

/** Whether the website and TMDB put the episode the same distance into the title. */
function absoluteNumberAgrees(episode: UnmatchedEpisodeOutput): boolean {
  const match = episode.best_match
  if (!match) return false
  return (
    episode.absolute_number !== null &&
    episode.absolute_number === match.absolute_number
  )
}

/**
 * How a record is numbered, marked where the two sides agree.
 *
 * A website and TMDB rarely number the same episode the same way, so a number
 * they do share is the strongest thing on the row for telling whether the match
 * is the right one, and it is picked out rather than left to be read off.
 */
function Numbering({
  seasonNumber,
  episodeNumber,
  absoluteNumber,
  seasonAndEpisodeMatches,
  absoluteMatches,
}: {
  seasonNumber: number | null
  episodeNumber: number | null
  absoluteNumber: number | null
  seasonAndEpisodeMatches: boolean
  absoluteMatches: boolean
}) {
  const seasonAndEpisode = seasonAndEpisodeText(seasonNumber, episodeNumber)

  return (
    <span className="flex items-center gap-2 tabular-nums">
      {seasonAndEpisode ? (
        <span className={seasonAndEpisodeMatches ? "text-destructive" : ""}>
          {seasonAndEpisode}
        </span>
      ) : null}
      {absoluteNumber === null ? null : (
        <span className={absoluteMatches ? "text-destructive" : ""}>
          #{absoluteNumber}
        </span>
      )}
    </span>
  )
}

export const tmdbMatchColumns: ColumnDef<UnmatchedEpisodeOutput>[] = [
  {
    id: "show_name",
    accessorFn: (row) => row.show_name ?? "Unnamed",
    header: "Show",
    cell: ({ row }) => (
      <WrappingCell className="max-w-48">
        {row.original.show_name ?? "Unnamed"}
      </WrappingCell>
    ),
  },
  {
    id: "source_name",
    accessorFn: (row) => row.source_name ?? "Unknown source",
    header: "Source",
    meta: { filterVariant: "select" },
    filterFn: "equalsString",
    cell: ({ row }) => (
      <WrappingCell className="max-w-32">
        {row.original.source_name ?? "Unknown source"}
      </WrappingCell>
    ),
  },
  {
    id: "season_name",
    accessorFn: (row) => row.season_name ?? "",
    header: "Season",
    cell: ({ row }) => (
      <WrappingCell className="max-w-40">
        {row.original.season_name ?? ""}
      </WrappingCell>
    ),
  },
  {
    id: "episode_name",
    accessorFn: (row) => row.name ?? "Unnamed",
    header: "Episode",
    cell: ({ row }) => (
      <WrappingCell className="max-w-64">
        <span className="font-medium">{row.original.name ?? "Unnamed"}</span>
        <span className="mt-0.5 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
          <Numbering
            seasonNumber={row.original.season_number}
            episodeNumber={row.original.episode_number}
            absoluteNumber={row.original.absolute_number}
            seasonAndEpisodeMatches={seasonAndEpisodeAgree(row.original)}
            absoluteMatches={absoluteNumberAgrees(row.original)}
          />
          {row.original.url ? (
            <a
              href={row.original.url}
              target="_blank"
              rel="noopener noreferrer"
              className="underline"
            >
              Source
            </a>
          ) : null}
        </span>
      </WrappingCell>
    ),
  },
  {
    id: "match_name",
    accessorFn: (row) => row.best_match?.name ?? "No match",
    header: "TMDB match",
    cell: ({ row }) => {
      const match = row.original.best_match
      if (!match) {
        return (
          <WrappingCell className="max-w-64 text-muted-foreground">
            No match
          </WrappingCell>
        )
      }
      return (
        <WrappingCell className="max-w-64">
          {match.name ?? "Unnamed"}
          <span className="mt-0.5 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
            <Numbering
              seasonNumber={match.season_number}
              episodeNumber={match.episode_number}
              absoluteNumber={match.absolute_number}
              seasonAndEpisodeMatches={seasonAndEpisodeAgree(row.original)}
              absoluteMatches={absoluteNumberAgrees(row.original)}
            />
            <span className="tabular-nums">id {match.tmdb_episode_id}</span>
            <TmdbLink url={match.url} />
          </span>
        </WrappingCell>
      )
    },
  },
  {
    id: "similarity",
    accessorFn: (row) => row.best_match?.similarity ?? 0,
    header: "Match %",
    meta: { filterVariant: "range" },
    cell: ({ row }) => {
      const match = row.original.best_match
      return (
        <span className="tabular-nums">
          {match ? `${Math.round(match.similarity * 100)}%` : ""}
        </span>
      )
    },
  },
  {
    id: "approve",
    header: "Approve",
    enableSorting: false,
    enableColumnFilter: false,
    cell: ({ row }) => <TmdbMatchApproval episode={row.original} />,
  },
]
