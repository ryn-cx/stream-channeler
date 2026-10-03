// TODO: Validate
import type { ColumnDef } from "@tanstack/react-table"

import type { EpisodeLinkHistoryOutput, EpisodeRecord } from "@/client"
import {
  MatchSummary,
  type Summarised,
} from "@/components/Admin/tmdbMatchColumns"
import { DateCell } from "@/components/Common/TableCells"
import { EditEpisodeById } from "@/components/Episodes/EditEpisodeById"
import { Badge } from "@/components/ui/badge"
import { EpisodeLinkHistoryUndoButton } from "./EpisodeLinkHistoryUndoButton"

const KIND_LABELS: Record<string, string> = {
  link: "Linked",
  ignored: "Ignored",
  absent: "Not on TMDB",
}

// TODO: Validate
const pluginSummarised = (record: EpisodeRecord): Summarised => ({
  source_key: record.source.key,
  plugin_name: record.source.plugin_name,
  source_id: record.source.id,
  title_id: record.title.id,
  season_id: record.season.id,
  title_name: record.title.name ?? null,
  title_year: record.title.year ?? null,
  title_url: record.title.url ?? null,
  season_name: record.season.name ?? null,
  season_url: record.season.url ?? null,
  season_number: record.season.season_number ?? null,
  episode_number: record.episode.episode_number ?? null,
  absolute_number: null,
  name: record.episode.name ?? null,
  description: record.episode.description ?? null,
  duration: record.episode.duration ?? null,
  air_date: record.episode.air_date ?? null,
  url: record.episode.url ?? null,
})

// TODO: Validate
const tmdbSummarised = (record: EpisodeRecord): Summarised => ({
  source_key: record.source.key,
  plugin_name: record.source.plugin_name,
  source_id: null,
  title_id: record.title.id,
  season_id: record.season.id,
  title_name: record.title.name ?? null,
  title_year: record.title.year ?? null,
  title_url: record.title.tmdb_url ?? null,
  season_name: record.season.name ?? null,
  season_url: record.season.tmdb_url ?? null,
  season_number: record.season.season_number ?? null,
  episode_number: record.episode.episode_number ?? null,
  absolute_number: null,
  name: record.episode.name ?? null,
  description: record.episode.description ?? null,
  duration: record.episode.duration ?? null,
  air_date: record.episode.air_date ?? null,
  url: record.episode.tmdb_url ?? null,
})

// TODO: Validate
export const episodeLinkHistoryColumns: ColumnDef<EpisodeLinkHistoryOutput>[] =
  [
    {
      id: "created_at",
      accessorFn: (row) => row.created_at,
      header: "When",
      meta: { filterVariant: "dateRange", cellClassName: "align-top" },
      cell: ({ row }) => <DateCell value={row.original.created_at} />,
    },
    {
      id: "kind",
      accessorFn: (row) => row.kind,
      header: "Action",
      meta: {
        filterVariant: "select",
        cellClassName: "align-top",
        filterOptions: [
          { label: "Linked", value: "link" },
          { label: "Ignored", value: "ignored" },
          { label: "Not on TMDB", value: "absent" },
        ],
      },
      filterFn: "equalsString",
      cell: ({ row }) => (
        <Badge variant={row.original.kind === "link" ? "secondary" : "outline"}>
          {KIND_LABELS[row.original.kind] ?? row.original.kind}
        </Badge>
      ),
    },
    {
      id: "title_name",
      accessorFn: (row) => row.episode.title.name ?? "",
      header: "Combined Episode",
      meta: { cellClassName: "align-top" },
      cell: ({ row }) => (
        <MatchSummary
          record={pluginSummarised(row.original.episode)}
          counterpart={
            row.original.tmdb ? tmdbSummarised(row.original.tmdb) : null
          }
          editEpisode={
            <EditEpisodeById episodeId={row.original.episode.episode.id} />
          }
        />
      ),
    },
    {
      id: "tmdb_title_name",
      accessorFn: (row) => row.tmdb?.title.name ?? "",
      header: "Linked To",
      meta: { cellClassName: "align-top" },
      cell: ({ row }) => {
        const tmdb = row.original.tmdb
        if (!tmdb) {
          return <span className="text-muted-foreground">-</span>
        }
        return (
          <MatchSummary
            record={tmdbSummarised(tmdb)}
            counterpart={pluginSummarised(row.original.episode)}
            editEpisode={
              <EditEpisodeById
                episodeId={tmdb.episode.id}
                label="Edit this TMDB episode"
              />
            }
            isTmdbSide
          />
        )
      },
    },
    {
      id: "source_key",
      accessorFn: (row) => row.episode.source.key,
      header: "Source",
      cell: ({ row }) => (
        <span className="text-muted-foreground text-sm">
          {row.original.episode.source.key}
        </span>
      ),
    },
    {
      id: "episode_name",
      accessorFn: (row) => row.episode.episode.name ?? "",
      header: "Episode name",
      cell: ({ row }) => (
        <span className="whitespace-normal wrap-break-word">
          {row.original.episode.episode.name ?? "Unnamed"}
        </span>
      ),
    },
    {
      id: "season_number",
      accessorFn: (row) => row.episode.season.season_number ?? 0,
      header: "Season #",
      cell: ({ row }) => (
        <span className="tabular-nums text-muted-foreground">
          {row.original.episode.season.season_number ?? "-"}
        </span>
      ),
    },
    {
      id: "episode_number",
      accessorFn: (row) => row.episode.episode.episode_number ?? 0,
      header: "Episode #",
      cell: ({ row }) => (
        <span className="tabular-nums text-muted-foreground">
          {row.original.episode.episode.episode_number ?? "-"}
        </span>
      ),
    },
    {
      id: "plugin_name",
      accessorFn: (row) => row.episode.source.plugin_name ?? "",
      header: "Plugin",
      cell: ({ row }) => (
        <span className="text-muted-foreground text-sm">
          {row.original.episode.source.plugin_name ?? "No plugin"}
        </span>
      ),
    },
    {
      id: "tmdb_episode_name",
      accessorFn: (row) => row.tmdb?.episode.name ?? "",
      header: "Linked Episode name",
      cell: ({ row }) => (
        <span className="whitespace-normal wrap-break-word">
          {row.original.tmdb?.episode.name ?? "-"}
        </span>
      ),
    },
    {
      id: "note",
      accessorFn: (row) => row.note ?? "",
      header: "Note",
      meta: { cellClassName: "align-top" },
      cell: ({ row }) => (
        <span className="text-muted-foreground text-sm">
          {row.original.note ?? "-"}
        </span>
      ),
    },
    {
      id: "actions",
      header: "Actions",
      meta: { cellClassName: "align-top" },
      enableSorting: false,
      enableColumnFilter: false,
      cell: ({ row }) => <EpisodeLinkHistoryUndoButton entry={row.original} />,
    },
  ]
