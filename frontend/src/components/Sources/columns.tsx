// TODO: Validate
import { Link } from "@tanstack/react-router"
import type { ColumnDef } from "@tanstack/react-table"
import { Film, Layers } from "lucide-react"
import type { SourceListPublic } from "@/client"
import {
  DateCell,
  ParentLinkCell,
  TruncatedCell,
} from "@/components/Common/TableCells"
import { TooltipIconLink } from "@/components/Common/TooltipIconLink"
import { extraText } from "@/lib/extra"
import { SourceActionsMenu } from "./ActionsMenu"

export type SourceTableData = SourceListPublic & { pending?: boolean }

export const sourceColumns: ColumnDef<SourceTableData>[] = [
  {
    accessorKey: "plugin_name",
    header: "Plugin",
    cell: ({ row }) => (
      <ParentLinkCell
        to="/plugin/$pluginId"
        params={{ pluginId: row.original.plugin_id }}
        name={row.original.plugin_name}
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
        <div className="flex items-center gap-2">
          <Link
            to="/source/$sourceKey"
            params={{ sourceKey: row.original.id }}
            className="font-medium text-primary hover:underline block max-w-48 whitespace-normal wrap-break-word"
          >
            {row.original.name || `No Name (${row.original.key})`}
          </Link>
          <TooltipIconLink label="Seasons">
            <Link
              to="/source/$sourceKey/seasons"
              params={{ sourceKey: row.original.id }}
              className="text-muted-foreground hover:text-foreground shrink-0"
              aria-label="Seasons"
            >
              <Layers className="size-4" />
            </Link>
          </TooltipIconLink>
          <TooltipIconLink label="Episodes">
            <Link
              to="/source/$sourceKey/episodes"
              params={{ sourceKey: row.original.id }}
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
    accessorKey: "favicon_url",
    header: "Favicon URL",
    cell: ({ row }) => <TruncatedCell value={row.original.favicon_url} />,
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
          <SourceActionsMenu source={row.original} />
        )}
      </div>
    ),
  },
]
