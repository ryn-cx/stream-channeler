// TODO: Validate
import { Link } from "@tanstack/react-router"
import type { ColumnDef } from "@tanstack/react-table"
import { Pencil, SquareArrowOutUpRight } from "lucide-react"
import { type ReactNode, useState } from "react"

import type { UnlockedEpisodeOutput, UnmatchedEpisodeOutput } from "@/client"
import { ClampedContent } from "@/components/ChannelCommon/ClampedContent"
import { TmdbLink } from "@/components/ChannelCommon/TmdbLink"
import { TooltipIconButton } from "@/components/Common/TooltipIconButton"
import { EditEpisodeById } from "@/components/Episodes/EditEpisodeById"
import EditSeason from "@/components/Seasons/Edit"
import { EditShowById } from "@/components/Shows/EditShowById"
import { buttonVariants } from "@/components/ui/button"
import { useSeason } from "@/hooks/useEntities"
import { cn } from "@/lib/utils"
import { TmdbMatchActions, TmdbMatchConfirmButton } from "./TmdbMatchActions"
import { useOpenEpisodeEditor } from "./tmdbMatchEditing"
import { type Numbered, numberingAgreement } from "./tmdbNumbering"

/**
 * A row of the table, which is a served record with the id the table keys rows
 * by beside it. The record names its episode, its season and its title as three
 * records rather than as one flattened row, so the id a table row needs is not
 * one of its own fields.
 */
export type TmdbMatchRow = UnmatchedEpisodeOutput & { id: string }

// TODO: Validate
/** Key each served record by its episode, which is what a row of the table is. */
export function asTmdbMatchRows<RecordT extends UnmatchedEpisodeOutput>(
  records: RecordT[],
): (RecordT & { id: string })[] {
  return records.map((record) => ({ ...record, id: record.episode.id }))
}

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
    <div className={cn("whitespace-normal wrap-break-word", className)}>
      {children}
    </div>
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
function isExactNameMatch(row: TmdbMatchRow): boolean {
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
  description: string | null
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
  url: string | null | undefined
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
function EpisodeEditButton({ episode }: { episode: TmdbMatchRow }) {
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
  href: string | null | undefined
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
    ? "text-blue-600 dark:text-blue-400"
    : "text-destructive"

  return (
    <WrappingCell className="max-w-72">
      {action}
      {/*
        Named even on the TMDB side, where it says TMDB twice and tells nobody
        anything, because the two columns are read across rather than down and a
        line one of them is missing puts everything below it out of step.
      */}
      <span className="block text-xs text-muted-foreground">
        {record.source_id ? (
          <Link
            to="/shows"
            search={{ source_id: record.source_id }}
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
          to="/seasons"
          search={{ show_id: record.show_id }}
          className="min-w-0 hover:underline"
        >
          {record.show_name ?? "Unnamed"}
          {record.show_year === null ? "" : ` ${record.show_year}`}
        </Link>
        <EditShowById showId={record.show_id} />
        <ExternalLinkButton
          url={record.show_url}
          label="Open this show on the site it came from"
        />
      </span>
      <span className="flex flex-wrap items-center gap-1 text-xs text-muted-foreground">
        <Link
          to="/episodes"
          search={{ season_id: record.season_id }}
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
              Episode {record.episode_number ?? "?"}
            </span>
            {record.absolute_number === null ? null : (
              <span
                className={
                  agreement.absolute ? agreeingNumber : "text-muted-foreground"
                }
              >
                {" "}
                (Absolute {record.absolute_number})
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
      {record.description ? (
        <ClampedContent lines={5} className="text-xs text-muted-foreground">
          {record.description}
        </ClampedContent>
      ) : null}
      {note}
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
  match: NonNullable<TmdbMatchRow["best_match"]>
}) {
  if (!match.already_used || !match.used_by?.length) {
    return null
  }
  return (
    <span className="mt-0.5 flex flex-wrap items-center gap-1 text-xs text-pink-600 dark:text-pink-400">
      Already used by
      {match.used_by.map((used) => (
        <span key={used.episode.id} className="inline-flex items-center gap-1">
          {[
            used.season.season_number == null
              ? null
              : `S${used.season.season_number}E${used.episode.episode_number ?? "?"}`,
            used.episode.name,
          ]
            .filter(Boolean)
            .join(" ")}
          <EditEpisodeById episodeId={used.episode.id} />
        </span>
      ))}
    </span>
  )
}

// TODO: Validate
/** The TMDB side of a row, in the shape the summary reads. */
function choiceSummarised(
  match: TmdbMatchRow["best_match"],
): Summarised | null {
  if (!match) return null
  return {
    source_name: match.source.name ?? null,
    plugin_name: match.source.plugin_name ?? null,
    source_id: null,
    show_id: match.show.id,
    season_id: match.season.id,
    show_name: match.show.name ?? null,
    show_year: match.show.year ?? null,
    show_url: match.show.tmdb_url ?? null,
    season_url: match.season.tmdb_url ?? null,
    season_number: match.season.season_number ?? null,
    episode_number: match.episode.episode_number ?? null,
    absolute_number: match.absolute_number ?? null,
    name: match.episode.name ?? null,
    description: match.episode.description ?? null,
    url: match.episode.tmdb_url ?? null,
  }
}

// TODO: Validate
function episodeSummarised(row: UnmatchedEpisodeOutput): Summarised {
  return {
    source_name: row.source.name ?? null,
    plugin_name: row.source.plugin_name ?? null,
    source_id: row.source.id,
    show_id: row.show.id,
    season_id: row.season.id,
    show_name: row.show.name ?? null,
    show_year: row.show.year ?? null,
    show_url: row.show.url ?? null,
    season_url: row.season.url ?? null,
    season_number: row.season.season_number ?? null,
    episode_number: row.episode.episode_number ?? null,
    absolute_number: row.absolute_number ?? null,
    name: row.episode.name ?? null,
    description: row.episode.description ?? null,
    url: row.episode.url ?? null,
  }
}

export const tmdbMatchColumns: ColumnDef<TmdbMatchRow>[] = [
  {
    id: "summary",
    accessorFn: (row) => row.show.name ?? "Unnamed",
    header: "Combined Episode",
    meta: { cellClassName: "align-top" },
    cell: ({ row }) => (
      <MatchSummary
        record={episodeSummarised(row.original)}
        counterpart={choiceSummarised(row.original.best_match)}
        editEpisode={<EpisodeEditButton episode={row.original} />}
      />
    ),
  },
  {
    id: "match_summary",
    accessorFn: (row) => row.best_match?.show.name ?? "No match",
    header: "TMDB by name",
    meta: { serverBacked: false, cellClassName: "align-top" },
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
          editEpisode={
            <EditEpisodeById
              episodeId={nameMatch.episode.id}
              label="Edit this TMDB episode"
            />
          }
          isTmdbSide
          action={
            <TmdbMatchConfirmButton
              episodeId={row.original.episode.id}
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
    accessorFn: (row) => row.season_episode_match?.show.name ?? "No match",
    header: "Episode Number → Episode Number",
    meta: { serverBacked: false, cellClassName: "align-top" },
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
          editEpisode={
            <EditEpisodeById
              episodeId={seasonEpisodeMatch.episode.id}
              label="Edit this TMDB episode"
            />
          }
          isTmdbSide
          action={
            <TmdbMatchConfirmButton
              episodeId={row.original.episode.id}
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
    accessorFn: (row) => row.absolute_number_match?.show.name ?? "No match",
    header: "Absolute Number → Absolute Number",
    meta: { serverBacked: false, cellClassName: "align-top" },
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
          editEpisode={
            <EditEpisodeById
              episodeId={absoluteMatch.episode.id}
              label="Edit this TMDB episode"
            />
          }
          isTmdbSide
          action={
            <TmdbMatchConfirmButton
              episodeId={row.original.episode.id}
              match={absoluteMatch}
              kind="absolute"
            />
          }
        />
      )
    },
  },
  {
    id: "episode_absolute_match_summary",
    accessorFn: (row) =>
      row.episode_number_absolute_match?.show.name ?? "No match",
    header: "Episode Number → Absolute Number",
    meta: { serverBacked: false, cellClassName: "align-top" },
    cell: ({ row }) => {
      const episodeAbsoluteMatch = row.original.episode_number_absolute_match
      const match = choiceSummarised(episodeAbsoluteMatch)
      if (!episodeAbsoluteMatch || !match) {
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
          note={<AlreadyUsedNote match={episodeAbsoluteMatch} />}
          editEpisode={
            <EditEpisodeById
              episodeId={episodeAbsoluteMatch.episode.id}
              label="Edit this TMDB episode"
            />
          }
          isTmdbSide
          action={
            <TmdbMatchConfirmButton
              episodeId={row.original.episode.id}
              match={episodeAbsoluteMatch}
              kind="episode_absolute"
            />
          }
        />
      )
    },
  },
  {
    id: "description_embedding_match_summary",
    accessorFn: (row) =>
      row.description_embedding_match?.show.name ?? "No match",
    header: "Description → Description (embedding)",
    meta: { serverBacked: false, cellClassName: "align-top" },
    cell: ({ row }) => {
      const descriptionMatch = row.original.description_embedding_match ?? null
      const match = choiceSummarised(descriptionMatch)
      if (!descriptionMatch || !match) {
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
          note={<AlreadyUsedNote match={descriptionMatch} />}
          editEpisode={
            <EditEpisodeById
              episodeId={descriptionMatch.episode.id}
              label="Edit this TMDB episode"
            />
          }
          isTmdbSide
          action={
            <TmdbMatchConfirmButton
              episodeId={row.original.episode.id}
              match={descriptionMatch}
              kind="description_embedding"
            />
          }
        />
      )
    },
  },
  {
    id: "description_blended_match_summary",
    accessorFn: (row) => row.description_blended_match?.show.name ?? "No match",
    header: "Description → Description (blended)",
    meta: { serverBacked: false, cellClassName: "align-top" },
    cell: ({ row }) => {
      const descriptionMatch = row.original.description_blended_match ?? null
      const match = choiceSummarised(descriptionMatch)
      if (!descriptionMatch || !match) {
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
          note={<AlreadyUsedNote match={descriptionMatch} />}
          editEpisode={
            <EditEpisodeById
              episodeId={descriptionMatch.episode.id}
              label="Edit this TMDB episode"
            />
          }
          isTmdbSide
          action={
            <TmdbMatchConfirmButton
              episodeId={row.original.episode.id}
              match={descriptionMatch}
              kind="description_blended"
            />
          }
        />
      )
    },
  },
  {
    id: "title_embedding_match_summary",
    accessorFn: (row) => row.title_embedding_match?.show.name ?? "No match",
    header: "Title → Title (embedding)",
    meta: { serverBacked: false, cellClassName: "align-top" },
    cell: ({ row }) => {
      const textMatch = row.original.title_embedding_match ?? null
      const match = choiceSummarised(textMatch)
      if (!textMatch || !match) {
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
          note={<AlreadyUsedNote match={textMatch} />}
          editEpisode={
            <EditEpisodeById
              episodeId={textMatch.episode.id}
              label="Edit this TMDB episode"
            />
          }
          isTmdbSide
          action={
            <TmdbMatchConfirmButton
              episodeId={row.original.episode.id}
              match={textMatch}
              kind="title_embedding"
            />
          }
        />
      )
    },
  },
  {
    id: "title_blended_match_summary",
    accessorFn: (row) => row.title_blended_match?.show.name ?? "No match",
    header: "Title → Title (blended)",
    meta: { serverBacked: false, cellClassName: "align-top" },
    cell: ({ row }) => {
      const textMatch = row.original.title_blended_match ?? null
      const match = choiceSummarised(textMatch)
      if (!textMatch || !match) {
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
          note={<AlreadyUsedNote match={textMatch} />}
          editEpisode={
            <EditEpisodeById
              episodeId={textMatch.episode.id}
              label="Edit this TMDB episode"
            />
          }
          isTmdbSide
          action={
            <TmdbMatchConfirmButton
              episodeId={row.original.episode.id}
              match={textMatch}
              kind="title_blended"
            />
          }
        />
      )
    },
  },
  {
    id: "show_name",
    accessorFn: (row) => row.show.name ?? "Unnamed",
    header: "Show",
    cell: ({ row }) => (
      <WrappingCell className="max-w-48">
        <Link
          to="/seasons"
          search={{ show_id: row.original.show.id }}
          className="hover:underline"
        >
          {row.original.show.name ?? "Unnamed"}
        </Link>
      </WrappingCell>
    ),
  },
  {
    id: "show_year",
    accessorFn: (row) => row.show.year ?? "",
    header: "Year",
    cell: ({ row }) => (
      <span className="tabular-nums">{row.original.show.year ?? ""}</span>
    ),
  },
  {
    id: "source_name",
    accessorFn: (row) => row.source.name ?? "Unknown source",
    header: "Source",
    meta: { filterVariant: "select" },
    filterFn: "equalsString",
    cell: ({ row }) => (
      <WrappingCell className="max-w-32">
        <Link
          to="/shows"
          search={{ source_id: row.original.source.id }}
          className="hover:underline"
        >
          {row.original.source.name ?? "Unknown source"}
        </Link>
      </WrappingCell>
    ),
  },
  {
    id: "season_name",
    accessorFn: (row) => row.season.name ?? "",
    header: "Season",
    cell: ({ row }) => (
      <WrappingCell className="max-w-40">
        <Link
          to="/episodes"
          search={{ season_id: row.original.season.id }}
          className="hover:underline"
        >
          {row.original.season.name ?? "Unnamed"}
        </Link>
      </WrappingCell>
    ),
  },
  {
    id: "season_number",
    accessorFn: (row) => row.season.season_number ?? "",
    header: "Season #",
    cell: ({ row }) => (
      <span className="tabular-nums">
        {row.original.season.season_number ?? ""}
      </span>
    ),
  },
  {
    id: "episode_number",
    accessorFn: (row) => row.episode.episode_number ?? "",
    header: "Episode #",
    cell: ({ row }) => (
      <span className="tabular-nums">
        {row.original.episode.episode_number ?? ""}
      </span>
    ),
  },
  {
    id: "absolute_number",
    accessorFn: (row) => row.absolute_number ?? "",
    header: "Absolute Number",
    meta: { serverBacked: false },
    cell: ({ row }) => (
      <span className="tabular-nums">{row.original.absolute_number ?? ""}</span>
    ),
  },
  {
    id: "episode_name",
    accessorFn: (row) => row.episode.name ?? "Unnamed",
    header: "Episode name",
    cell: ({ row }) => (
      <WrappingCell className="max-w-64">
        <span
          className={cn(
            "font-medium",
            isExactNameMatch(row.original) && "text-destructive",
          )}
        >
          {row.original.episode.name ?? "Unnamed"}
        </span>
        {row.original.episode.url ? (
          <a
            href={row.original.episode.url}
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
    accessorFn: (row) => row.best_match?.show.name ?? "",
    header: "Match show",
    meta: { serverBacked: false },
    cell: ({ row }) => (
      <WrappingCell className="max-w-48">
        <SummaryLink href={row.original.best_match?.show.tmdb_url ?? null}>
          {row.original.best_match?.show.name ?? ""}
        </SummaryLink>
      </WrappingCell>
    ),
  },
  {
    id: "match_show_year",
    accessorFn: (row) => row.best_match?.show.year ?? "",
    header: "Match year",
    meta: { serverBacked: false },
    cell: ({ row }) => (
      <span className="tabular-nums">
        {row.original.best_match?.show.year ?? ""}
      </span>
    ),
  },
  {
    id: "match_season_number",
    accessorFn: (row) => row.best_match?.season.season_number ?? "",
    header: "Match season #",
    meta: { serverBacked: false },
    cell: ({ row }) => (
      <span className="tabular-nums">
        {row.original.best_match?.season.season_number ?? ""}
      </span>
    ),
  },
  {
    id: "match_episode_number",
    accessorFn: (row) => row.best_match?.episode.episode_number ?? "",
    header: "Match episode #",
    meta: { serverBacked: false },
    cell: ({ row }) => (
      <span className="tabular-nums">
        {row.original.best_match?.episode.episode_number ?? ""}
      </span>
    ),
  },
  {
    id: "match_absolute_number",
    accessorFn: (row) => row.best_match?.absolute_number ?? "",
    header: "Match absolute number",
    meta: { serverBacked: false },
    cell: ({ row }) => (
      <span className="tabular-nums">
        {row.original.best_match?.absolute_number ?? ""}
      </span>
    ),
  },
  {
    id: "match_name",
    accessorFn: (row) => row.best_match?.episode.name ?? "No match",
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
          {match.episode.name ?? "Unnamed"}
          <span className="mt-0.5 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
            <span className="tabular-nums">id {match.episode.tmdb_id}</span>
            <TmdbLink url={match.episode.tmdb_url ?? null} />
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
    accessorFn: (row) => row.episode.canonical_episode_note ?? "",
    header: "Note",
    cell: ({ row }) => (
      <WrappingCell className="max-w-48 text-xs text-muted-foreground">
        {row.original.episode.canonical_episode_note ?? ""}
      </WrappingCell>
    ),
  },
  {
    id: "actions",
    header: "Actions",
    meta: { cellClassName: "align-top" },
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
