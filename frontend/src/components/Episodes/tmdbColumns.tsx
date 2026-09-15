// TODO: Validate
import type { ColumnDef } from "@tanstack/react-table"
import type { TmdbEpisodeListOutput } from "@/client"
import { DateCell, TruncatedCell } from "@/components/Common/TableCells"
import { extraText } from "@/lib/extra"

export type TmdbEpisodeTableData = TmdbEpisodeListOutput

// TODO: Validate
export const tmdbEpisodeColumns: ColumnDef<TmdbEpisodeTableData>[] = [
  {
    accessorKey: "tmdb_title_name",
    header: "Title",
    cell: ({ row }) => <TruncatedCell value={row.original.tmdb_title_name} />,
  },
  {
    accessorKey: "tmdb_season_name",
    header: "Season",
    cell: ({ row }) => <TruncatedCell value={row.original.tmdb_season_name} />,
  },
  {
    accessorKey: "name",
    header: "Name",
    cell: ({ row }) => (
      <span className="font-medium block max-w-48 whitespace-normal wrap-break-word">
        {row.original.name ||
          `No Name (${row.original.key ?? row.original.id})`}
      </span>
    ),
  },
  {
    accessorKey: "key",
    header: "Key",
    cell: ({ row }) => <TruncatedCell value={row.original.key} />,
  },
  {
    accessorKey: "episode_number",
    header: "Episode #",
    meta: { filterVariant: "range" },
    cell: ({ row }) => (
      <span className="text-muted-foreground">
        {row.original.episode_number ?? "-"}
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
    accessorKey: "description",
    header: "Description",
    cell: ({ row }) => <TruncatedCell value={row.original.description} />,
  },
  {
    accessorKey: "image_url",
    header: "Image URL",
    cell: ({ row }) => <TruncatedCell value={row.original.image_url} />,
  },
  {
    accessorKey: "thumbnail_url",
    header: "Thumbnail URL",
    cell: ({ row }) => <TruncatedCell value={row.original.thumbnail_url} />,
  },
  {
    accessorKey: "air_date",
    header: "Air Date",
    meta: { filterVariant: "dateRange" },
    cell: ({ row }) => (
      <span className="text-muted-foreground text-sm">
        {row.original.air_date ?? "-"}
      </span>
    ),
  },
  {
    accessorKey: "duration",
    header: "Duration",
    meta: { filterVariant: "range" },
    cell: ({ row }) => (
      <span className="text-muted-foreground">
        {row.original.duration ?? "-"}
      </span>
    ),
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
    accessorKey: "tmdb_title_key",
    header: "Title Key",
    cell: ({ row }) => <TruncatedCell value={row.original.tmdb_title_key} />,
  },
  {
    accessorKey: "status",
    header: "Status",
    cell: ({ row }) => <TruncatedCell value={row.original.status} />,
  },
  {
    accessorKey: "data_timestamp",
    header: "Data Timestamp",
    meta: { filterVariant: "dateRange" },
    cell: ({ row }) => <DateCell value={row.original.data_timestamp} />,
  },
  {
    accessorKey: "update_at",
    header: "Update At",
    meta: { filterVariant: "dateRange" },
    cell: ({ row }) => <DateCell value={row.original.update_at} />,
  },
  {
    accessorKey: "deleted_at",
    header: "Deleted At",
    meta: { filterVariant: "dateRange" },
    cell: ({ row }) => <DateCell value={row.original.deleted_at} />,
  },
  {
    accessorKey: "extra",
    header: "Extra",
    cell: ({ row }) => <TruncatedCell value={extraText(row.original.extra)} />,
  },
  {
    accessorKey: "tmdb_title_id",
    header: "Title ID",
    cell: ({ row }) => <TruncatedCell value={row.original.tmdb_title_id} />,
  },
  {
    accessorKey: "tmdb_season_id",
    header: "Season ID",
    cell: ({ row }) => <TruncatedCell value={row.original.tmdb_season_id} />,
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
