// TODO: Validate
import { Link } from "@tanstack/react-router"
import type { ColumnDef } from "@tanstack/react-table"
import { Clapperboard, FileText, Film, Layers } from "lucide-react"
import type { PluginListOutput } from "@/client"
import { DateCell, TruncatedCell } from "@/components/Common/TableCells"
import { TooltipIconLink } from "@/components/Common/TooltipIconLink"
import { extraText } from "@/lib/extra"
import { PluginActionsMenu } from "./ActionsMenu"

export type PluginTableData = PluginListOutput & { pending?: boolean }

// TODO: Validate
export function pluginColumns(isAdmin = false): ColumnDef<PluginTableData>[] {
  return [
    {
      accessorKey: "name",
      header: "Name",
      cell: ({ row }) => {
        const label = row.original.name || `No Name (${row.original.key})`
        if (row.original.pending) {
          return (
            <span className="font-medium text-muted-foreground">{label}</span>
          )
        }
        return (
          <div className="flex items-center gap-2">
            <Link
              to="/sources"
              search={{ plugin_id: row.original.id }}
              className="font-medium text-primary hover:underline"
            >
              {label}
            </Link>
            {isAdmin && (
              <TooltipIconLink label="Files">
                <Link
                  to="/files"
                  search={{ plugin_id: row.original.id }}
                  className="text-muted-foreground hover:text-foreground"
                  aria-label="Files"
                >
                  <FileText className="size-4" />
                </Link>
              </TooltipIconLink>
            )}
            <TooltipIconLink label="Shows">
              <Link
                to="/shows"
                search={{ plugin_id: row.original.id }}
                className="text-muted-foreground hover:text-foreground"
                aria-label="Shows"
              >
                <Clapperboard className="size-4" />
              </Link>
            </TooltipIconLink>
            <TooltipIconLink label="Seasons">
              <Link
                to="/seasons"
                search={{ plugin_id: row.original.id }}
                className="text-muted-foreground hover:text-foreground"
                aria-label="Seasons"
              >
                <Layers className="size-4" />
              </Link>
            </TooltipIconLink>
            <TooltipIconLink label="Episodes">
              <Link
                to="/episodes"
                search={{ plugin_id: row.original.id }}
                className="text-muted-foreground hover:text-foreground"
                aria-label="Episodes"
              >
                <Film className="size-4" />
              </Link>
            </TooltipIconLink>
          </div>
        )
      },
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
      cell: ({ row }) => (
        <TruncatedCell value={extraText(row.original.extra)} />
      ),
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
            <PluginActionsMenu plugin={row.original} />
          )}
        </div>
      ),
    },
  ]
}
