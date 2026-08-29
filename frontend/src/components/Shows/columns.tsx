// TODO: Validate
import { Link } from "@tanstack/react-router"
import type { ColumnDef } from "@tanstack/react-table"
import { Film } from "lucide-react"
import type { ShowListPublic } from "@/client"
import {
  DateCell,
  ParentLinkCell,
  TruncatedCell,
} from "@/components/Common/TableCells"
import { TooltipIconLink } from "@/components/Common/TooltipIconLink"
import { extraText } from "@/lib/extra"
import { ShowActionsMenu } from "./ActionsMenu"

export type ShowTableData = ShowListPublic & { pending?: boolean }

export const showColumns: ColumnDef<ShowTableData>[] = [
  {
    accessorKey: "plugin_name",
    header: "Plugin",
    cell: ({ row }) => (
      <ParentLinkCell
        to="/sources"
        search={{ plugin_id: row.original.plugin_id }}
        name={row.original.plugin_name}
      />
    ),
  },
  {
    accessorKey: "source_name",
    header: "Source",
    cell: ({ row }) => (
      <ParentLinkCell
        to="/shows"
        search={{ source_id: row.original.source_id }}
        name={row.original.source_name}
      />
    ),
  },
  {
    accessorKey: "name",
    header: "Name",
    cell: ({ row }) =>
      row.original.pending ? (
        <span className="font-medium text-primary block max-w-48 whitespace-normal wrap-break-word">
          {row.original.name || `No Name (${row.original.key})`}
        </span>
      ) : (
        <div className="flex items-center gap-2">
          <Link
            to="/seasons"
            search={{ show_id: row.original.id }}
            className="font-medium text-primary hover:underline block max-w-48 whitespace-normal wrap-break-word"
          >
            {row.original.name || `No Name (${row.original.key})`}
          </Link>
          <TooltipIconLink label="Episodes">
            <Link
              to="/episodes"
              search={{ show_id: row.original.id }}
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
    accessorKey: "tmdb_id",
    header: "TMDB ID",
    meta: { filterVariant: "range" },
    cell: ({ row }) => (
      <span className="text-muted-foreground">
        {row.original.tmdb_id ?? "-"}
      </span>
    ),
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
    accessorKey: "year",
    header: "Year",
    cell: ({ row }) => (
      <span className="tabular-nums">{row.original.year ?? ""}</span>
    ),
  },
  {
    accessorKey: "canonical_show_validated_at",
    header: "Link Validated At",
    meta: { filterVariant: "dateRange" },
    cell: ({ row }) => (
      <DateCell value={row.original.canonical_show_validated_at} />
    ),
  },
  {
    accessorKey: "extra",
    header: "Extra",
    cell: ({ row }) => <TruncatedCell value={extraText(row.original.extra)} />,
  },
  {
    accessorKey: "key",
    header: "Key",
    cell: ({ row }) => <TruncatedCell value={row.original.key} />,
  },
  {
    accessorKey: "id",
    header: "ID",
    cell: ({ row }) => <TruncatedCell value={row.original.id} />,
  },
  {
    id: "actions",
    enableSorting: false,
    enableColumnFilter: false,
    header: () => <span className="sr-only">Actions</span>,
    cell: ({ row }) => (
      <div className="flex justify-end">
        {row.original.pending ? null : <ShowActionsMenu show={row.original} />}
      </div>
    ),
  },
]
