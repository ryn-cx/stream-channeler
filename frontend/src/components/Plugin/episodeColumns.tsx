// TODO: Validate
import type { ColumnDef } from "@tanstack/react-table"

import DeleteEpisode from "./DeleteEpisode"
import EditEpisode from "./EditEpisode"

export interface EpisodeTableData {
  key: string
  name: string | null
  id: string
  season_id: string
  episode_number: number | null
  url: string | null
  description: string | null
  image_url: string | null
  release_date: string | null
  air_date: string | null
  duration: number | null
  sort_order: number | null
  data_timestamp: string | null
}

export const episodeColumns: ColumnDef<EpisodeTableData>[] = [
  {
    accessorKey: "name",
    header: "Name",
    cell: ({ row }) => (
      <span className="font-medium">
        {row.original.name || `No Name (${row.original.key})`}
      </span>
    ),
  },
  {
    accessorKey: "episode_number",
    header: "Episode #",
    cell: ({ row }) => (
      <span className="text-muted-foreground">
        {row.original.episode_number ?? "-"}
      </span>
    ),
  },
  {
    accessorKey: "sort_order",
    header: "Sort Order",
    cell: ({ row }) => (
      <span className="text-muted-foreground">
        {row.original.sort_order ?? "-"}
      </span>
    ),
  },
  {
    accessorKey: "url",
    header: "URL",
    cell: ({ row }) => (
      <span className="text-muted-foreground text-sm truncate max-w-48 block">
        {row.original.url ?? "-"}
      </span>
    ),
  },
  {
    accessorKey: "description",
    header: "Description",
    cell: ({ row }) => (
      <span className="text-muted-foreground text-sm truncate max-w-48 block">
        {row.original.description ?? "-"}
      </span>
    ),
  },
  {
    accessorKey: "image_url",
    header: "Image URL",
    cell: ({ row }) => (
      <span className="text-muted-foreground text-sm truncate max-w-48 block">
        {row.original.image_url ?? "-"}
      </span>
    ),
  },
  {
    accessorKey: "release_date",
    header: "Release Date",
    cell: ({ row }) => (
      <span className="text-muted-foreground text-sm">
        {row.original.release_date ?? "-"}
      </span>
    ),
  },
  {
    accessorKey: "air_date",
    header: "Air Date",
    cell: ({ row }) => (
      <span className="text-muted-foreground text-sm">
        {row.original.air_date ?? "-"}
      </span>
    ),
  },
  {
    accessorKey: "duration",
    header: "Duration",
    cell: ({ row }) => (
      <span className="text-muted-foreground">
        {row.original.duration ?? "-"}
      </span>
    ),
  },
  {
    accessorKey: "data_timestamp",
    header: "Data Timestamp",
    cell: ({ row }) => (
      <span className="text-muted-foreground text-sm">
        {row.original.data_timestamp
          ? new Date(row.original.data_timestamp).toLocaleString()
          : "-"}
      </span>
    ),
  },
  {
    accessorKey: "key",
    header: "Key",
    cell: ({ row }) => (
      <span className="text-muted-foreground font-mono text-sm">
        {row.original.key}
      </span>
    ),
  },
  {
    accessorKey: "id",
    header: "ID",
    cell: ({ row }) => (
      <span className="text-muted-foreground font-mono text-sm">
        {row.original.id}
      </span>
    ),
  },
  {
    id: "actions",
    header: () => <span className="sr-only">Actions</span>,
    enableHiding: false,
    cell: ({ row }) => (
      <div className="flex justify-end">
        <EditEpisode episode={row.original} />
        <DeleteEpisode episode={row.original} />
      </div>
    ),
  },
]
