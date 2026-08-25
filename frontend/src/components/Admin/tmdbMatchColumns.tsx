// TODO: Validate
import { Link } from "@tanstack/react-router"
import type { ColumnDef } from "@tanstack/react-table"
import { Pencil, SquareArrowOutUpRight } from "lucide-react"
import { type ReactNode, useState } from "react"

import type { UnlockedEpisodeOutput, UnmatchedEpisodeOutput } from "@/client"
import { TmdbLink } from "@/components/ChannelCommon/TmdbLink"
import { TooltipIconButton } from "@/components/Common/TooltipIconButton"
import { EditEpisodeById } from "@/components/Episodes/EditEpisodeById"
import EditSeason from "@/components/Seasons/Edit"
import EditShow from "@/components/Shows/Edit"
import { buttonVariants } from "@/components/ui/button"
import { useSeason, useShow } from "@/hooks/useEntities"
import { cn } from "@/lib/utils"
import { TmdbMatchActions, TmdbMatchConfirmButton } from "./TmdbMatchActions"
import { useOpenEpisodeEditor } from "./tmdbMatchEditing"
import { type Numbered, numberingAgreement } from "./tmdbNumbering"

// TODO: Validate
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

// TODO: Validate
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

/** As much of one side of a row as the summary column reads. */
interface Summarised extends Numbered {
  source_name: string | null
  plugin_name: string | null
  show_name: string | null
  show_year: number | null
  show_url: string | null
  season_url: string | null
  name: string | null
  url: string | null
  /** The rows themselves, for the pages this site holds them on. */
  source_id: string | null
  show_id: string
  season_id: string
}

// TODO: Validate
function ExternalLinkButton({
  url,
  label,
}: {
  url: string | null
  label: string
}) {
  if (!url) return null
  return (
    <a
      href={url}
      target="_blank"
      rel="noopener noreferrer"
      title={label}
      aria-label={label}
      className={cn(
        buttonVariants({ variant: "outline", size: "icon-sm" }),
        "bg-muted dark:bg-muted/50",
      )}
    >
      <SquareArrowOutUpRight />
    </a>
  )
}

// TODO: Validate
function ShowEditButton({ showId }: { showId: string }) {
  const [isOpen, setIsOpen] = useState(false)
  const { data: show } = useShow(isOpen ? showId : undefined)
  return (
    <>
      <TooltipIconButton
        label="Edit this show"
        icon={<Pencil />}
        size="icon-sm"
        onClick={() => setIsOpen(true)}
      />
      {isOpen && show ? (
        <EditShow show={show} open onOpenChange={setIsOpen} />
      ) : null}
    </>
  )
}

// TODO: Validate
function SeasonEditButton({ seasonId }: { seasonId: string }) {
  const [isOpen, setIsOpen] = useState(false)
  const { data: season } = useSeason(isOpen ? seasonId : undefined)
  return (
    <>
      <TooltipIconButton
        label="Edit this season"
        icon={<Pencil />}
        size="icon-sm"
        onClick={() => setIsOpen(true)}
      />
      {isOpen && season ? (
        <EditSeason season={season} open onOpenChange={setIsOpen} />
      ) : null}
    </>
  )
}

// TODO: Validate
function EpisodeEditButton({ episode }: { episode: UnmatchedEpisodeOutput }) {
  const openEditor = useOpenEpisodeEditor()
  if (!openEditor) return null
  return (
    <TooltipIconButton
      label="Edit this episode"
      icon={<Pencil />}
      size="icon-sm"
      onClick={() => openEditor(episode)}
    />
  )
}

// TODO: Validate
/** Text that opens its own page, or plain text where there is no page to open. */
function SummaryLink({
  href,
  className,
  children,
}: {
  href: string | null
  className?: string
  children: ReactNode
}) {
  if (!href) {
    return <span className={className}>{children}</span>
  }
  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className={cn("hover:underline", className)}
    >
      {children}
    </a>
  )
}

// TODO: Validate
/**
 * One side of a row, read as the title, the season and the episode within it.
 *
 * Everything that says which episode this is, in the order somebody checking a
 * match reads it: the title first, since a wrong match is most often a match to
 * another title altogether, then the season, then the episode. Each line opens
 * the page it names, so a row can be checked against the site it came from
 * without leaving the table to find it.
 *
 * A number the other side agrees with is picked out, since two sides rarely
 * number an episode the same way and a number they share is the strongest thing
 * on the row for saying the match is right.
 */
function MatchSummary({
  record,
  counterpart,
  note,
  action,
  editEpisode,
  isTmdbSide,
}: {
  record: Summarised
  counterpart: Numbered | null
  note?: ReactNode
  action?: ReactNode
  editEpisode?: ReactNode
  isTmdbSide?: boolean
}) {
  const agreement = numberingAgreement(
    record,
    counterpart ?? NOTHING_TO_AGREE_WITH,
  )
  const seasonsAgree =
    isTmdbSide === true &&
    record.season_number !== null &&
    record.season_number === (counterpart?.season_number ?? null)
  const agreeingNumber = seasonsAgree
    ? "text-emerald-600 dark:text-emerald-400"
    : "text-destructive"

  return (
    <WrappingCell className="max-w-72">
      {/*
        Named even on the TMDB side, where it says TMDB twice and tells nobody
        anything, because the two columns are read across rather than down and a
        line one of them is missing puts everything below it out of step.
      */}
      <span className="block text-xs text-muted-foreground">
        {record.source_id ? (
          <Link
            to="/source/$sourceKey"
            params={{ sourceKey: record.source_id }}
            className="hover:underline"
          >
            {record.source_name ?? "Unknown source"}
            {record.plugin_name ? ` · ${record.plugin_name}` : ""}
          </Link>
        ) : (
          <>
            {record.source_name ?? "Unknown source"}
            {record.plugin_name ? ` · ${record.plugin_name}` : ""}
          </>
        )}
      </span>
      <span className="flex flex-wrap items-center gap-1 font-medium">
        <Link
          to="/show/$showKey"
          params={{ showKey: record.show_id }}
          className="min-w-0 hover:underline"
        >
          {record.show_name ?? "Unnamed"}
          {record.show_year === null ? "" : ` ${record.show_year}`}
        </Link>
        <ShowEditButton showId={record.show_id} />
        <ExternalLinkButton
          url={record.show_url}
          label="Open this show on the site it came from"
        />
      </span>
      <span className="flex flex-wrap items-center gap-1 text-xs text-muted-foreground">
        <Link
          to="/season/$seasonKey"
          params={{ seasonKey: record.season_id }}
          className="min-w-0 hover:underline"
        >
          Season {record.season_number ?? "?"}
        </Link>
        <SeasonEditButton seasonId={record.season_id} />
        <ExternalLinkButton
          url={record.season_url}
          label="Open this season on the site it came from"
        />
      </span>
      <span className="flex flex-wrap items-center gap-1 text-xs">
        <span className="min-w-0">
          <span className="tabular-nums">
            <span
              className={
                agreement.seasonAndEpisode
                  ? agreeingNumber
                  : "text-muted-foreground"
              }
            >
              {record.episode_number ?? "?"}
            </span>
            {record.absolute_number === null ? null : (
              <span
                className={
                  agreement.absolute ? agreeingNumber : "text-muted-foreground"
                }
              >
                {" "}
                ({record.absolute_number})
              </span>
            )}
          </span>{" "}
          {record.name ?? "Unnamed"}
        </span>
        {editEpisode}
        <ExternalLinkButton
          url={record.url}
          label="Open this episode on the site it came from"
        />
      </span>
      {note}
      {action}
    </WrappingCell>
  )
}

// TODO: Validate
/**
 * Which of the listing's other episodes already point at this TMDB episode.
 *
 * A suggestion another episode of the same listing has already been settled on
 * is one to doubt, since two episodes of one listing are rarely the same TMDB
 * episode, and the one already using it is named so the pair can be compared
 * rather than only counted.
 */
function AlreadyUsedNote({
  match,
}: {
  match: NonNullable<UnmatchedEpisodeOutput["best_match"]>
}) {
  if (!match.already_used || !match.used_by?.length) {
    return null
  }
  return (
    <span className="mt-0.5 flex flex-wrap items-center gap-1 text-xs text-destructive">
      Already used by
      {match.used_by.map((episode) => (
        <span key={episode.id} className="inline-flex items-center gap-1">
          {[
            episode.season_number === null
              ? null
              : `S${episode.season_number}E${episode.episode_number ?? "?"}`,
            episode.name,
          ]
            .filter(Boolean)
            .join(" ")}
          <EditEpisodeById episodeId={episode.id} />
        </span>
      ))}
    </span>
  )
}

// TODO: Validate
/** The TMDB side of a row, in the shape the summary reads. */
function choiceSummarised(
  match: UnmatchedEpisodeOutput["best_match"],
): Summarised | null {
  if (!match) return null
  return {
    source_name: match.source_name,
    plugin_name: match.plugin_name,
    source_id: null,
    show_id: match.show_id,
    season_id: match.season_id,
    show_name: match.show_name,
    show_year: match.show_year,
    show_url: match.show_url,
    season_url: match.season_url,
    season_number: match.season_number,
    episode_number: match.episode_number,
    absolute_number: match.absolute_number,
    name: match.name,
    url: match.url,
  }
}

// TODO: Validate
function episodeSummarised(row: UnmatchedEpisodeOutput): Summarised {
  return {
    source_name: row.source_name,
    plugin_name: row.plugin_name,
    source_id: row.source_id,
    show_id: row.show_id,
    season_id: row.season_id,
    show_name: row.show_name,
    show_year: row.show_year,
    show_url: row.show_url,
    season_url: row.season_url,
    season_number: row.season_number,
    episode_number: row.episode_number ?? null,
    absolute_number: row.absolute_number ?? null,
    name: row.name ?? null,
    url: row.url ?? null,
  }
}

export const tmdbMatchColumns: ColumnDef<UnmatchedEpisodeOutput>[] = [
  {
    id: "summary",
    accessorFn: (row) => row.show_name ?? "Unnamed",
    header: "Combined Episode",
    cell: ({ row }) => (
      <MatchSummary
        record={episodeSummarised(row.original)}
        counterpart={row.original.best_match}
        editEpisode={<EpisodeEditButton episode={row.original} />}
      />
    ),
  },
  {
    id: "match_summary",
    accessorFn: (row) => row.best_match?.show_name ?? "No match",
    header: "TMDB by name",
    meta: { serverBacked: false },
    cell: ({ row }) => {
      const nameMatch = row.original.best_match
      const match = choiceSummarised(nameMatch)
      if (!nameMatch || !match) {
        return (
          <WrappingCell className="max-w-72 text-muted-foreground">
            No match
          </WrappingCell>
        )
      }
      return (
        <MatchSummary
          record={match}
          counterpart={episodeSummarised(row.original)}
          note={<AlreadyUsedNote match={nameMatch} />}
          isTmdbSide
          action={
            <TmdbMatchConfirmButton
              episodeId={row.original.id}
              match={nameMatch}
              kind="name"
            />
          }
        />
      )
    },
  },
  {
    id: "number_match_summary",
    accessorFn: (row) => row.season_episode_match?.show_name ?? "No match",
    header: "TMDB by season & episode #",
    meta: { serverBacked: false },
    cell: ({ row }) => {
      const seasonEpisodeMatch = row.original.season_episode_match
      const match = choiceSummarised(seasonEpisodeMatch)
      if (!seasonEpisodeMatch || !match) {
        return (
          <WrappingCell className="max-w-72 text-muted-foreground">
            No match
          </WrappingCell>
        )
      }
      return (
        <MatchSummary
          record={match}
          counterpart={episodeSummarised(row.original)}
          note={<AlreadyUsedNote match={seasonEpisodeMatch} />}
          isTmdbSide
          action={
            <TmdbMatchConfirmButton
              episodeId={row.original.id}
              match={seasonEpisodeMatch}
              kind="season_episode"
            />
          }
        />
      )
    },
  },
  {
    id: "absolute_match_summary",
    accessorFn: (row) => row.absolute_number_match?.show_name ?? "No match",
    header: "TMDB by sequential #",
    meta: { serverBacked: false },
    cell: ({ row }) => {
      const absoluteMatch = row.original.absolute_number_match
      const match = choiceSummarised(absoluteMatch)
      if (!absoluteMatch || !match) {
        return (
          <WrappingCell className="max-w-72 text-muted-foreground">
            No match
          </WrappingCell>
        )
      }
      return (
        <MatchSummary
          record={match}
          counterpart={episodeSummarised(row.original)}
          note={<AlreadyUsedNote match={absoluteMatch} />}
          isTmdbSide
          action={
            <TmdbMatchConfirmButton
              episodeId={row.original.id}
              match={absoluteMatch}
              kind="absolute"
            />
          }
        />
      )
    },
  },
  {
    id: "show_name",
    accessorFn: (row) => row.show_name ?? "Unnamed",
    header: "Show",
    cell: ({ row }) => (
      <WrappingCell className="max-w-48">
        <Link
          to="/show/$showKey"
          params={{ showKey: row.original.show_id }}
          className="hover:underline"
        >
          {row.original.show_name ?? "Unnamed"}
        </Link>
      </WrappingCell>
    ),
  },
  {
    id: "show_year",
    accessorFn: (row) => row.show_year ?? "",
    header: "Year",
    cell: ({ row }) => (
      <span className="tabular-nums">{row.original.show_year ?? ""}</span>
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
        <Link
          to="/source/$sourceKey"
          params={{ sourceKey: row.original.source_id }}
          className="hover:underline"
        >
          {row.original.source_name ?? "Unknown source"}
        </Link>
      </WrappingCell>
    ),
  },
  {
    id: "season_name",
    accessorFn: (row) => row.season_name ?? "",
    header: "Season",
    cell: ({ row }) => (
      <WrappingCell className="max-w-40">
        <Link
          to="/season/$seasonKey"
          params={{ seasonKey: row.original.season_id }}
          className="hover:underline"
        >
          {row.original.season_name ?? "Unnamed"}
        </Link>
      </WrappingCell>
    ),
  },
  {
    id: "season_number",
    accessorFn: (row) => row.season_number ?? "",
    header: "Season #",
    cell: ({ row }) => (
      <span className="tabular-nums">{row.original.season_number ?? ""}</span>
    ),
  },
  {
    id: "episode_number",
    accessorFn: (row) => row.episode_number ?? "",
    header: "Episode #",
    cell: ({ row }) => (
      <span className="tabular-nums">{row.original.episode_number ?? ""}</span>
    ),
  },
  {
    id: "absolute_number",
    accessorFn: (row) => row.absolute_number ?? "",
    header: "Sequential #",
    meta: { serverBacked: false },
    cell: ({ row }) => (
      <span className="tabular-nums">{row.original.absolute_number ?? ""}</span>
    ),
  },
  {
    id: "episode_name",
    accessorFn: (row) => row.name ?? "Unnamed",
    header: "Episode name",
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
        {row.original.url ? (
          <a
            href={row.original.url}
            target="_blank"
            rel="noopener noreferrer"
            className="mt-0.5 block text-xs text-muted-foreground underline"
          >
            Source
          </a>
        ) : null}
      </WrappingCell>
    ),
  },
  {
    id: "match_show_name",
    accessorFn: (row) => row.best_match?.show_name ?? "",
    header: "Match show",
    meta: { serverBacked: false },
    cell: ({ row }) => (
      <WrappingCell className="max-w-48">
        <SummaryLink href={row.original.best_match?.show_url ?? null}>
          {row.original.best_match?.show_name ?? ""}
        </SummaryLink>
      </WrappingCell>
    ),
  },
  {
    id: "match_show_year",
    accessorFn: (row) => row.best_match?.show_year ?? "",
    header: "Match year",
    meta: { serverBacked: false },
    cell: ({ row }) => (
      <span className="tabular-nums">
        {row.original.best_match?.show_year ?? ""}
      </span>
    ),
  },
  {
    id: "match_season_number",
    accessorFn: (row) => row.best_match?.season_number ?? "",
    header: "Match season #",
    meta: { serverBacked: false },
    cell: ({ row }) => (
      <span className="tabular-nums">
        {row.original.best_match?.season_number ?? ""}
      </span>
    ),
  },
  {
    id: "match_episode_number",
    accessorFn: (row) => row.best_match?.episode_number ?? "",
    header: "Match episode #",
    meta: { serverBacked: false },
    cell: ({ row }) => (
      <span className="tabular-nums">
        {row.original.best_match?.episode_number ?? ""}
      </span>
    ),
  },
  {
    id: "match_absolute_number",
    accessorFn: (row) => row.best_match?.absolute_number ?? "",
    header: "Match sequential #",
    meta: { serverBacked: false },
    cell: ({ row }) => (
      <span className="tabular-nums">
        {row.original.best_match?.absolute_number ?? ""}
      </span>
    ),
  },
  {
    id: "match_name",
    accessorFn: (row) => row.best_match?.name ?? "No match",
    header: "Match episode name",
    meta: { serverBacked: false },
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
    meta: { filterVariant: "range", serverBacked: false },
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
    id: "identifier_note",
    accessorFn: (row) => row.canonical_episode_note ?? "",
    header: "Note",
    cell: ({ row }) => (
      <WrappingCell className="max-w-48 text-xs text-muted-foreground">
        {row.original.canonical_episode_note ?? ""}
      </WrappingCell>
    ),
  },
  {
    id: "actions",
    header: "Actions",
    enableSorting: false,
    enableColumnFilter: false,
    cell: ({ row }) => <TmdbMatchActions episode={row.original} />,
  },
]

/**
 * The split columns start hidden, since the two summaries carry what they say.
 *
 * Every value has a column of its own so it can be sorted and filtered on, but
 * showing all of them at once is a table nobody can read across. The summaries
 * are what the page opens as, and a column is turned on when there is a reason
 * to sort by that one value.
 */
export const TMDB_MATCH_DEFAULT_VISIBILITY = {
  show_name: false,
  show_year: false,
  season_name: false,
  season_number: false,
  episode_number: false,
  absolute_number: false,
  episode_name: false,
  match_show_name: false,
  match_show_year: false,
  match_season_number: false,
  match_episode_number: false,
  match_absolute_number: false,
  match_name: false,
}
