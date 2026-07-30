// TODO: Validate
import { Link } from "@tanstack/react-router"
import type { ColumnDef } from "@tanstack/react-table"
import { Clapperboard, FileText, Film, Layers } from "lucide-react"
import type { PluginListOutput } from "@/client"
import type { OwnerView } from "@/components/Common/DataTable"
import { DateCell, TruncatedCell } from "@/components/Common/TableCells"
import { TooltipIconLink } from "@/components/Common/TooltipIconLink"
import { cn } from "@/lib/utils"
import { visibilityDotClass, visibilityLabel } from "@/lib/visibility"

import { PluginActionsMenu } from "./ActionsMenu"

export type PluginTableData = PluginListOutput & { pending?: boolean }

export function pluginColumns(
  _scope: OwnerView,
  isAdmin = false,
): ColumnDef<PluginTableData>[] {
  return [
    {
      accessorKey: "username",
      header: "User",
      cell: ({ row }) => <TruncatedCell value={row.original.username} />,
    },
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
              to="/plugin/$pluginId"
              params={{ pluginId: row.original.id }}
              className="font-medium text-primary hover:underline"
            >
              {label}
            </Link>
            {isAdmin && (
              <TooltipIconLink label="Files">
                <Link
                  to="/plugin/$pluginId/files"
                  params={{ pluginId: row.original.id }}
                  className="text-muted-foreground hover:text-foreground"
                  aria-label="Files"
                >
                  <FileText className="size-4" />
                </Link>
              </TooltipIconLink>
            )}
            <TooltipIconLink label="Shows">
              <Link
                to="/plugin/$pluginId/shows"
                params={{ pluginId: row.original.id }}
                className="text-muted-foreground hover:text-foreground"
                aria-label="Shows"
              >
                <Clapperboard className="size-4" />
              </Link>
            </TooltipIconLink>
            <TooltipIconLink label="Seasons">
              <Link
                to="/plugin/$pluginId/seasons"
                params={{ pluginId: row.original.id }}
                className="text-muted-foreground hover:text-foreground"
                aria-label="Seasons"
              >
                <Layers className="size-4" />
              </Link>
            </TooltipIconLink>
            <TooltipIconLink label="Episodes">
              <Link
                to="/plugin/$pluginId/episodes"
                params={{ pluginId: row.original.id }}
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
      cell: ({ row }) => <TruncatedCell value={row.original.extra} />,
    },
    {
      accessorFn: (row) => visibilityLabel(row.visibility),
      id: "visibility",
      header: "Visibility",
      meta: { filterVariant: "select" },
      filterFn: "equalsString",
      cell: ({ row }) => {
        const visibility = row.original.visibility
        return (
          <div className="flex items-center gap-2">
            <span
              className={cn(
                "size-2 rounded-full",
                visibilityDotClass(visibility),
              )}
            />
            <span
              className={
                visibility === "private" ? "text-muted-foreground" : ""
              }
            >
              {visibilityLabel(visibility)}
            </span>
          </div>
        )
      },
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
