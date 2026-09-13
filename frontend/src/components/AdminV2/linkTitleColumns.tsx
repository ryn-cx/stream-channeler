// TODO: Validate
import type { ColumnDef } from "@tanstack/react-table"

import type { MissingSourceTitleOutput } from "@/client"
import { DateCell } from "@/components/Common/TableCells"
import { EditTitleById } from "@/components/Titles/EditTitleById"
import { LinkTitleImportForm } from "./LinkTitleImportForm"

// TODO: Validate
export const linkTitleColumns: ColumnDef<MissingSourceTitleOutput>[] = [
  {
    id: "name",
    accessorFn: (row) => row.name ?? "",
    header: "Title",
    cell: ({ row }) => (
      <span className="flex items-center gap-2">
        <span className="font-medium whitespace-normal wrap-break-word">
          {row.original.name || `No Name (${row.original.key})`}
        </span>
        <EditTitleById titleId={row.original.id} />
      </span>
    ),
  },
  {
    id: "year",
    accessorFn: (row) => row.year ?? 0,
    header: "Year",
    cell: ({ row }) => (
      <span className="text-muted-foreground">{row.original.year ?? "-"}</span>
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
          {row.original.tmdb_id}
        </a>
      ) : (
        <span className="text-muted-foreground">-</span>
      ),
  },
  {
    id: "created_at",
    accessorFn: (row) => row.created_at,
    header: "Added",
    meta: { filterVariant: "dateRange" },
    cell: ({ row }) => <DateCell value={row.original.created_at} />,
  },
  {
    id: "actions",
    header: "Source URL",
    enableSorting: false,
    cell: ({ row }) => <LinkTitleImportForm title={row.original} />,
  },
]
