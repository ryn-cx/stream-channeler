// TODO: Validate
import type { ColumnDef } from "@tanstack/react-table"

import type { DuplicatedCanonicalEpisodeOutput } from "@/client"
import { DuplicatedCanonicalEpisodeLinks } from "./DuplicatedCanonicalEpisodeLinks"

export const duplicatedCanonicalEpisodeColumns: ColumnDef<DuplicatedCanonicalEpisodeOutput>[] =
  [
    {
      id: "source_name",
      accessorFn: (row) => row.source.name ?? "",
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
      id: "show_name",
      accessorFn: (row) => row.canonical.show.name ?? "",
      header: "Canonical Show",
      cell: ({ row }) => {
        const show = row.original.canonical.show
        const url = show.tmdb_url ?? show.url
        return url ? (
          <a
            href={url}
            target="_blank"
            rel="noreferrer"
            className="hover:underline"
          >
            {show.name ?? "Unnamed"}
          </a>
        ) : (
          (show.name ?? "Unnamed")
        )
      },
    },
    {
      id: "show_year",
      accessorFn: (row) => row.canonical.show.year ?? 0,
      header: "Year",
      cell: ({ row }) => row.original.canonical.show.year ?? "",
    },
    {
      id: "season_number",
      accessorFn: (row) => row.canonical.season.season_number ?? 0,
      header: "Season",
    },
    {
      id: "episode_number",
      accessorFn: (row) => row.canonical.episode.episode_number ?? 0,
      header: "Episode",
    },
    {
      id: "name",
      accessorFn: (row) => row.canonical.episode.name ?? "",
      header: "Canonical Episode",
      cell: ({ row }) => {
        const episode = row.original.canonical.episode
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
      accessorFn: (row) => row.canonical.episode.key,
      header: "Key",
      cell: ({ row }) => (
        <span className="font-mono text-xs">
          {row.original.canonical.episode.key}
        </span>
      ),
    },
    {
      id: "canonical_plugin_name",
      accessorFn: (row) => row.canonical.source.plugin_name ?? "",
      header: "Canonical Plugin",
      meta: { filterVariant: "select" },
      filterFn: "equalsString",
    },
    {
      id: "canonical_source_name",
      accessorFn: (row) => row.canonical.source.name ?? "",
      header: "Canonical Source",
      meta: { filterVariant: "select" },
      filterFn: "equalsString",
    },
    {
      id: "linked_episodes",
      accessorFn: (row) => row.linked_episodes.length,
      header: "Linked Episodes",
      enableSorting: false,
      cell: ({ row }) => (
        <DuplicatedCanonicalEpisodeLinks
          episodes={row.original.linked_episodes}
        />
      ),
    },
  ]
