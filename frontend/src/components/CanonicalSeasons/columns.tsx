// TODO: Validate
import { Link } from "@tanstack/react-router"
import type { ColumnDef } from "@tanstack/react-table"
import type { CanonicalSeasonListOutput } from "@/client"
import {
  DateCell,
  ParentLinkCell,
  TruncatedCell,
} from "@/components/Common/TableCells"

export type CanonicalSeasonTableData = CanonicalSeasonListOutput

export const canonicalSeasonColumns: ColumnDef<CanonicalSeasonTableData>[] = [
  {
    accessorKey: "canonical_show_name",
    header: "Show",
    cell: ({ row }) => (
      <ParentLinkCell
        to="/admin/canonical-show/$canonicalShowId"
        params={{ canonicalShowId: row.original.canonical_show_id }}
        name={row.original.canonical_show_name}
      />
    ),
  },
  {
    accessorKey: "name",
    header: "Name",
    cell: ({ row }) => (
      <Link
        to="/admin/canonical-season/$canonicalSeasonId"
        params={{ canonicalSeasonId: row.original.id }}
        className="font-medium text-primary hover:underline block max-w-48 whitespace-normal wrap-break-word"
      >
        {row.original.name ||
          `No Name (${row.original.key ?? row.original.id})`}
      </Link>
    ),
  },
  {
    accessorKey: "key",
    header: "Key",
    cell: ({ row }) => <TruncatedCell value={row.original.key} />,
  },
  {
    accessorKey: "season_number",
    header: "Season #",
    meta: { filterVariant: "range" },
    cell: ({ row }) => (
      <span className="text-muted-foreground">
        {row.original.season_number ?? "-"}
      </span>
    ),
  },
  {
    accessorKey: "sort_order",
    header: "Sort Order",
    meta: { filterVariant: "range" },
    cell: ({ row }) => (
      <span className="text-muted-foreground">
        {row.original.sort_order ?? "-"}
      </span>
    ),
  },
  {
    accessorKey: "url",
    header: "URL",
    cell: ({ row }) => <TruncatedCell value={row.original.url} />,
  },
  {
    accessorKey: "image_url",
    header: "Image URL",
    cell: ({ row }) => <TruncatedCell value={row.original.image_url} />,
  },
  // Read out of the key rather than stored, so there is no column to sort or
  // filter by. The key itself is there for both.
  {
    accessorKey: "tmdb_id",
    header: "TMDB ID",
    enableSorting: false,
    enableColumnFilter: false,
    cell: ({ row }) => (
      <span className="text-muted-foreground">
        {row.original.tmdb_id ?? "-"}
      </span>
    ),
  },
  {
    accessorKey: "canonical_show_key",
    header: "Show Key",
    cell: ({ row }) => (
      <TruncatedCell value={row.original.canonical_show_key} />
    ),
  },
  {
    accessorKey: "created_at",
    header: "Created At",
    meta: { filterVariant: "dateRange" },
    cell: ({ row }) => <DateCell value={row.original.created_at} />,
  },
  {
    accessorKey: "modified_at",
    header: "Modified At",
    meta: { filterVariant: "dateRange" },
    cell: ({ row }) => <DateCell value={row.original.modified_at} />,
  },
  {
    accessorKey: "id",
    header: "ID",
    cell: ({ row }) => <TruncatedCell value={row.original.id} />,
  },
]
