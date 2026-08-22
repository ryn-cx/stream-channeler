// TODO: Validate
import type { ColumnDef } from "@tanstack/react-table"

import type { DuplicatedCanonicalEpisodeOutput } from "@/client"
import { DuplicatedCanonicalEpisodeLinks } from "./DuplicatedCanonicalEpisodeLinks"

export const duplicatedCanonicalEpisodeColumns: ColumnDef<DuplicatedCanonicalEpisodeOutput>[] =
  [
    {
      id: "source_name",
      accessorFn: (row) => row.source_name ?? "",
      header: "Colliding Source",
      meta: { filterVariant: "select" },
      filterFn: "equalsString",
    },
    {
      id: "plugin_name",
      accessorFn: (row) => row.plugin_name ?? "",
      header: "Colliding Plugin",
      meta: { filterVariant: "select" },
      filterFn: "equalsString",
    },
    {
      id: "show_name",
      accessorFn: (row) => row.show_name ?? "",
      header: "Canonical Show",
      cell: ({ row }) =>
        row.original.show_url ? (
          <a
            href={row.original.show_url}
            target="_blank"
            rel="noreferrer"
            className="hover:underline"
          >
            {row.original.show_name ?? "Unnamed"}
          </a>
        ) : (
          (row.original.show_name ?? "Unnamed")
        ),
    },
    {
      id: "show_year",
      accessorFn: (row) => row.show_year ?? 0,
      header: "Year",
      cell: ({ row }) => row.original.show_year ?? "",
    },
    {
      id: "season_number",
      accessorFn: (row) => row.season_number ?? 0,
      header: "Season",
    },
    {
      id: "episode_number",
      accessorFn: (row) => row.episode_number ?? 0,
      header: "Episode",
    },
    {
      id: "name",
      accessorFn: (row) => row.name ?? "",
      header: "Canonical Episode",
      cell: ({ row }) =>
        row.original.url ? (
          <a
            href={row.original.url}
            target="_blank"
            rel="noreferrer"
            className="hover:underline"
          >
            {row.original.name ?? "Unnamed"}
          </a>
        ) : (
          (row.original.name ?? "Unnamed")
        ),
    },
    {
      id: "key",
      accessorFn: (row) => row.key,
      header: "Key",
      cell: ({ row }) => (
        <span className="font-mono text-xs">{row.original.key}</span>
      ),
    },
    {
      id: "canonical_plugin_name",
      accessorFn: (row) => row.canonical_plugin_name ?? "",
      header: "Canonical Plugin",
      meta: { filterVariant: "select" },
      filterFn: "equalsString",
    },
    {
      id: "canonical_source_name",
      accessorFn: (row) => row.canonical_source_name ?? "",
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
