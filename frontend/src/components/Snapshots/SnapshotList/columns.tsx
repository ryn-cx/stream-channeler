// TODO: Validate
import { Link } from "@tanstack/react-router"
import type { ColumnDef } from "@tanstack/react-table"

import type { SnapshotAdminOutput } from "@/client"
import { CopyId } from "@/components/Common/CopyId"
import { cn } from "@/lib/utils"
import { visibilityDotClass, visibilityLabel } from "@/lib/visibility"
import { SnapshotActionsMenu } from "./SnapshotActionsMenu"

export type SnapshotTableData = SnapshotAdminOutput & { pending?: boolean }

export const columns: ColumnDef<SnapshotTableData>[] = [
  {
    accessorKey: "id",
    header: "ID",
    cell: ({ row }) => <CopyId id={row.original.id} />,
  },
  {
    accessorKey: "name",
    header: "Name",
    cell: ({ row }) =>
      row.original.pending ? (
        <span className="text-muted-foreground">
          {row.original.name ?? "(untitled)"}
        </span>
      ) : (
        <Link
          to="/snapshots/$snapshotId"
          params={{ snapshotId: row.original.id }}
          className="hover:underline text-primary"
        >
          {row.original.name ?? "(untitled)"}
        </Link>
      ),
    meta: {
      filterVariant: "text",
    },
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
            className={visibility === "private" ? "text-muted-foreground" : ""}
          >
            {visibilityLabel(visibility)}
          </span>
        </div>
      )
    },
  },
  {
    accessorKey: "created_at",
    header: "Saved",
    meta: { filterVariant: "dateRange" },
    cell: ({ row }) => (
      <span className="text-muted-foreground">
        {new Date(row.original.created_at).toLocaleDateString()}
      </span>
    ),
  },
  {
    id: "actions",
    enableSorting: false,
    enableColumnFilter: false,
    header: () => <span className="sr-only">Actions</span>,
    cell: ({ row }) => (
      <div className="flex justify-end">
        {row.original.pending ? null : (
          <SnapshotActionsMenu snapshot={row.original} />
        )}
      </div>
    ),
  },
]
