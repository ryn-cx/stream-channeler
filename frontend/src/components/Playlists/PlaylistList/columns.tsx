// TODO: Validate
import { Link } from "@tanstack/react-router"
import type { ColumnDef } from "@tanstack/react-table"

import type { PlaylistOutput } from "@/client"
import { CopyId } from "@/components/Common/CopyId"
import { cn } from "@/lib/utils"
import { visibilityDotClass, visibilityLabel } from "@/lib/visibility"
import DeletePlaylist from "./DeletePlaylist"
import EditPlaylist from "./EditPlaylist"

export const columns: ColumnDef<PlaylistOutput>[] = [
  {
    accessorKey: "id",
    header: "ID",
    cell: ({ row }) => <CopyId id={row.original.id} />,
  },
  {
    accessorKey: "name",
    header: "Name",
    cell: ({ row }) => (
      <Link
        to="/playlists/$playlistId"
        params={{ playlistId: row.original.id }}
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
    cell: ({ row }) => (
      <span className="text-muted-foreground">
        {new Date(row.original.created_at).toLocaleDateString()}
      </span>
    ),
  },
  {
    id: "actions",
    header: () => <span className="sr-only">Actions</span>,
    cell: ({ row }) => (
      <div className="flex justify-end">
        <EditPlaylist playlist={row.original} />
        <DeletePlaylist id={row.original.id} />
      </div>
    ),
  },
]
