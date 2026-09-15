// TODO: Validate
import type { ColumnDef } from "@tanstack/react-table"

import type { UnmatchedTitleOutput } from "@/client"
import { DateCell } from "@/components/Common/TableCells"
import { EditTitleById } from "@/components/Titles/EditTitleById"
import { UnmatchedTitleDeleteButton } from "./UnmatchedTitleDeleteButton"
import { UnmatchedTitleIgnoreButton } from "./UnmatchedTitleIgnoreButton"
import { UnmatchedTitleImportForm } from "./UnmatchedTitleImportForm"

// TODO: Validate
export const linkTitleColumns: ColumnDef<UnmatchedTitleOutput>[] = [
  {
    id: "title_name",
    accessorFn: (row) => row.title_name ?? "",
    header: "Title",
    cell: ({ row }) => (
      <span className="flex items-center gap-2">
        <span className="font-medium whitespace-normal wrap-break-word">
          {row.original.title_name ?? "Unnamed"}
        </span>
        <EditTitleById titleId={row.original.title_id} />
      </span>
    ),
  },
  {
    id: "provider_name",
    accessorFn: (row) => row.provider_name,
    header: "Source",
    cell: ({ row }) => (
      <span className="whitespace-normal wrap-break-word">
        {row.original.provider_name}
      </span>
    ),
  },
  {
    id: "plugin_key",
    accessorFn: (row) => row.plugin_key ?? "",
    header: "Plugin",
    cell: ({ row }) => (
      <span className="text-muted-foreground text-sm">
        {row.original.plugin_key ?? "No plugin"}
      </span>
    ),
  },
  {
    id: "title_year",
    accessorFn: (row) => row.title_year ?? 0,
    header: "Year",
    cell: ({ row }) => (
      <span className="text-muted-foreground">
        {row.original.title_year ?? "-"}
      </span>
    ),
  },
  {
    id: "media_type",
    accessorFn: (row) => row.media_type ?? "",
    header: "Media Type",
    meta: { filterVariant: "select" },
    filterFn: "equalsString",
    cell: ({ row }) => (
      <span className="text-muted-foreground">
        {row.original.media_type ?? "-"}
      </span>
    ),
  },
  {
    id: "channel_count",
    accessorFn: (row) => row.channel_count,
    header: "Channels",
    enableSorting: false,
    enableColumnFilter: false,
    cell: ({ row }) => (
      <span className="text-muted-foreground">
        {row.original.channel_count}
      </span>
    ),
  },
  {
    id: "episode_count",
    accessorFn: (row) => row.episode_count,
    header: "Episodes",
    enableSorting: false,
    enableColumnFilter: false,
    cell: ({ row }) => (
      <span className="text-muted-foreground">
        {row.original.episode_count}
      </span>
    ),
  },
  {
    id: "tmdb_url",
    header: "TMDB",
    enableSorting: false,
    enableColumnFilter: false,
    cell: ({ row }) =>
      row.original.tmdb_url ? (
        <a
          href={row.original.tmdb_url}
          target="_blank"
          rel="noreferrer"
          className="text-primary hover:underline text-sm"
        >
          Open
        </a>
      ) : (
        <span className="text-muted-foreground">-</span>
      ),
  },
  {
    id: "created_at",
    header: "Found",
    enableSorting: false,
    enableColumnFilter: false,
    cell: ({ row }) => <DateCell value={row.original.created_at} />,
  },
  {
    id: "actions",
    header: "Source URL",
    enableSorting: false,
    enableColumnFilter: false,
    cell: ({ row }) => (
      <span className="flex items-center gap-2">
        <UnmatchedTitleImportForm unmatchedTitle={row.original} />
        <UnmatchedTitleIgnoreButton unmatchedTitle={row.original} />
        <UnmatchedTitleDeleteButton unmatchedTitle={row.original} />
      </span>
    ),
  },
]
