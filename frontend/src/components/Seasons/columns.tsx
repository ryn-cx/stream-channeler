// TODO: Validate
import { Link } from "@tanstack/react-router"
import type { ColumnDef } from "@tanstack/react-table"
import type { SeasonListOutput } from "@/client"
import {
  DateCell,
  ParentLinkCell,
  TruncatedCell,
} from "@/components/Common/TableCells"
import { extraText } from "@/lib/extra"
import { SeasonActionsMenu } from "./ActionsMenu"

export type SeasonTableData = SeasonListOutput & { pending?: boolean }

export const seasonColumns: ColumnDef<SeasonTableData>[] = [
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
    accessorKey: "show_name",
    header: "Show",
    cell: ({ row }) => (
      <ParentLinkCell
        to="/seasons"
        search={{ show_id: row.original.show_id }}
        name={row.original.show_name}
      />
    ),
  },
  {
    accessorKey: "name",
    header: "Name",
    cell: ({ row }) =>
      row.original.pending ? (
        <span className="font-medium text-muted-foreground block max-w-48 whitespace-normal wrap-break-word">
          {row.original.name || `No Name (${row.original.key})`}
        </span>
      ) : (
        <Link
          to="/episodes"
          search={{ season_id: row.original.id }}
          className="font-medium text-primary hover:underline block max-w-48 whitespace-normal wrap-break-word"
        >
          {row.original.name || `No Name (${row.original.key})`}
        </Link>
      ),
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
        {row.original.pending ? null : (
          <SeasonActionsMenu season={row.original} />
        )}
      </div>
    ),
  },
]
