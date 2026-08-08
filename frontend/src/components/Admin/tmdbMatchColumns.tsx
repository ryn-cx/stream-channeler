// TODO: Validate
import type { ColumnDef } from "@tanstack/react-table"
import type { ReactNode } from "react"

import type { UnlockedEpisodeOutput, UnmatchedEpisodeOutput } from "@/client"
import { TmdbLink } from "@/components/ChannelCommon/TmdbLink"
import { cn } from "@/lib/utils"
import { TmdbMatchApproval } from "./TmdbMatchApproval"
import {
  type Numbered,
  numberingAgreement,
  seasonAndEpisodeText,
} from "./tmdbNumbering"

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

/**
 * Whether the website and TMDB give an episode the very same name.
 *
 * An episode both agree the name and the number of is locked as it is stored,
 * so one that is named the same and still listed here is one they disagree
 * about the number of. Only the unlocked episodes carry this, and a row without
 * it is one there is nothing to say about.
 */
function isExactNameMatch(row: UnmatchedEpisodeOutput): boolean {
  return (row as Partial<UnlockedEpisodeOutput>).name_matches === true
}

const NOTHING_TO_AGREE_WITH: Numbered = {
  season_number: null,
  episode_number: null,
  absolute_number: null,
}

/**
 * How a record is numbered, marked where the other record puts it in the same place.
 *
 * A website and TMDB rarely number the same episode the same way, so a number
 * they do share is the strongest thing on the row for telling whether the match
 * is the right one, and it is picked out rather than left to be read off. Each
 * number is marked on its own, since the two sides can agree through one of
 * them without agreeing through the other.
 */
function Numbering({
  record,
  counterpart,
}: {
  record: Numbered
  counterpart: Numbered | null
}) {
  const seasonAndEpisode = seasonAndEpisodeText(record)
  const agreement = numberingAgreement(
    record,
    counterpart ?? NOTHING_TO_AGREE_WITH,
  )

  return (
    <span className="flex items-center gap-2 tabular-nums">
      {seasonAndEpisode ? (
        <span className={agreement.seasonAndEpisode ? "text-destructive" : ""}>
          {seasonAndEpisode}
        </span>
      ) : null}
      {record.absolute_number === null ? null : (
        <span className={agreement.absolute ? "text-destructive" : ""}>
          #{record.absolute_number}
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
        <span
          className={cn(
            "font-medium",
            isExactNameMatch(row.original) && "text-destructive",
          )}
        >
          {row.original.name ?? "Unnamed"}
        </span>
        <span className="mt-0.5 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
          <Numbering
            record={row.original}
            counterpart={row.original.best_match}
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
            <Numbering record={match} counterpart={row.original} />
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
