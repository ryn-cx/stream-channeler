// TODO: Validate
import { Link } from "@tanstack/react-router"
import type { ColumnDef } from "@tanstack/react-table"
import { Film } from "lucide-react"
import type { CanonicalShowOutput } from "@/client"
import { DateCell, TruncatedCell } from "@/components/Common/TableCells"
import { TooltipIconLink } from "@/components/Common/TooltipIconLink"

export type CanonicalShowTableData = CanonicalShowOutput

export const canonicalShowColumns: ColumnDef<CanonicalShowTableData>[] = [
  {
    accessorKey: "name",
    header: "Name",
    cell: ({ row }) => (
      <div className="flex items-center gap-2">
        <Link
          to="/admin/canonical-show/$canonicalShowId"
          params={{ canonicalShowId: row.original.id }}
          className="font-medium text-primary hover:underline block max-w-48 whitespace-normal wrap-break-word"
        >
          {row.original.name ||
            `No Name (${row.original.key ?? row.original.id})`}
        </Link>
        <TooltipIconLink label="Episodes">
          <Link
            to="/admin/canonical-show/$canonicalShowId/episodes"
            params={{ canonicalShowId: row.original.id }}
            className="text-muted-foreground hover:text-foreground shrink-0"
            aria-label="Episodes"
          >
            <Film className="size-4" />
          </Link>
        </TooltipIconLink>
      </div>
    ),
  },
  {
    accessorKey: "key",
    header: "Key",
    cell: ({ row }) => <TruncatedCell value={row.original.key} />,
  },
  {
    accessorKey: "media_type",
    header: "Media Type",
    cell: ({ row }) => (
      <span className="text-muted-foreground">
        {row.original.media_type ?? "-"}
      </span>
    ),
  },
  {
    accessorKey: "description",
    header: "Description",
    cell: ({ row }) => <TruncatedCell value={row.original.description} />,
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
  {
    accessorKey: "icon",
    header: "Icon",
    cell: ({ row }) => (
      <span className="text-muted-foreground">{row.original.icon ?? "-"}</span>
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
    accessorKey: "tmdb_url",
    header: "TMDB URL",
    enableSorting: false,
    enableColumnFilter: false,
    cell: ({ row }) => <TruncatedCell value={row.original.tmdb_url} />,
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
