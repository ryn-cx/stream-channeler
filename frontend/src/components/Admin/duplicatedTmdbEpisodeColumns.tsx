// TODO: Validate
import type { ColumnDef } from "@tanstack/react-table"

import type { DuplicatedTmdbEpisodeOutput } from "@/client"
import { DuplicatedTmdbEpisodeLinks } from "./DuplicatedTmdbEpisodeLinks"

export const duplicatedTmdbEpisodeColumns: ColumnDef<DuplicatedTmdbEpisodeOutput>[] =
  [
    {
      id: "source_key",
      accessorFn: (row) => row.source.key,
      header: "Colliding Source",
      meta: { filterVariant: "select" },
      filterFn: "equalsString",
    },
    {
      id: "plugin_name",
      accessorFn: (row) => row.source.plugin_name ?? "",
      header: "Colliding Plugin",
      meta: { filterVariant: "select" },
      filterFn: "equalsString",
    },
    {
      id: "title_name",
      accessorFn: (row) => row.tmdb.title.name ?? "",
      header: "TMDB Title",
      cell: ({ row }) => {
        const title = row.original.tmdb.title
        const url = title.tmdb_url ?? title.url
        return url ? (
          <a
            href={url}
            target="_blank"
            rel="noreferrer"
            className="hover:underline"
          >
            {title.name ?? "Unnamed"}
          </a>
        ) : (
          (title.name ?? "Unnamed")
        )
      },
    },
    {
      id: "title_year",
      accessorFn: (row) => row.tmdb.title.year ?? 0,
      header: "Year",
      cell: ({ row }) => row.original.tmdb.title.year ?? "",
    },
    {
      id: "season_number",
      accessorFn: (row) => row.tmdb.season.season_number ?? 0,
      header: "Season",
    },
    {
      id: "episode_number",
      accessorFn: (row) => row.tmdb.episode.episode_number ?? 0,
      header: "Episode",
    },
    {
      id: "name",
      accessorFn: (row) => row.tmdb.episode.name ?? "",
      header: "TMDB Episode",
      cell: ({ row }) => {
        const episode = row.original.tmdb.episode
        const url = episode.tmdb_url ?? episode.url
        return url ? (
          <a
            href={url}
            target="_blank"
            rel="noreferrer"
            className="hover:underline"
          >
            {episode.name ?? "Unnamed"}
          </a>
        ) : (
          (episode.name ?? "Unnamed")
        )
      },
    },
    {
      id: "key",
      accessorFn: (row) => row.tmdb.episode.key,
      header: "Key",
      cell: ({ row }) => (
        <span className="font-mono text-xs">
          {row.original.tmdb.episode.key}
        </span>
      ),
    },
    {
      id: "tmdb_plugin_name",
      accessorFn: (row) => row.tmdb.source.plugin_name ?? "",
      header: "TMDB Plugin",
      meta: { filterVariant: "select" },
      filterFn: "equalsString",
    },
    {
      id: "tmdb_source_key",
      accessorFn: (row) => row.tmdb.source.key,
      header: "TMDB Source",
      meta: { filterVariant: "select" },
      filterFn: "equalsString",
    },
    {
      id: "linked_episodes",
      accessorFn: (row) => row.linked_episodes.length,
      header: "Linked Episodes",
      enableSorting: false,
      cell: ({ row }) => (
        <DuplicatedTmdbEpisodeLinks episodes={row.original.linked_episodes} />
      ),
    },
  ]
