// TODO: Validate
import type { ColumnDef } from "@tanstack/react-table"
import type { EpisodeListOutput } from "@/client"
import {
  DateCell,
  ParentLinkCell,
  TruncatedCell,
} from "@/components/Common/TableCells"

import { EpisodeActionsMenu } from "./ActionsMenu"

export type EpisodeTableData = EpisodeListOutput & { pending?: boolean }

export const episodeColumns: ColumnDef<EpisodeTableData>[] = [
  {
    accessorKey: "username",
    header: "User",
    cell: ({ row }) => <TruncatedCell value={row.original.username} />,
  },
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
    accessorKey: "source_name",
    header: "Source",
    cell: ({ row }) => (
      <ParentLinkCell
        to="/source/$sourceKey"
        params={{ sourceKey: row.original.source_id }}
        name={row.original.source_name}
      />
    ),
  },
  {
    accessorKey: "show_name",
    header: "Show",
    cell: ({ row }) => (
      <ParentLinkCell
        to="/show/$showKey"
        params={{ showKey: row.original.show_id }}
        name={row.original.show_name}
      />
    ),
  },
  {
    accessorKey: "season_name",
    header: "Season",
    cell: ({ row }) => (
      <ParentLinkCell
        to="/season/$seasonKey"
        params={{ seasonKey: row.original.season_id }}
        name={row.original.season_name}
      />
    ),
  },
  {
    accessorKey: "name",
    header: "Name",
    cell: ({ row }) => (
      <span
        className={
          row.original.pending
            ? "font-medium text-muted-foreground block max-w-48 whitespace-normal wrap-break-word"
            : "font-medium block max-w-48 whitespace-normal wrap-break-word"
        }
      >
        {row.original.name || `No Name (${row.original.key})`}
      </span>
    ),
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
    accessorKey: "release_date",
    header: "Release Date",
    meta: { filterVariant: "dateRange" },
    cell: ({ row }) => (
      <span className="text-muted-foreground text-sm">
        {row.original.release_date ?? "-"}
      </span>
    ),
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
          <EpisodeActionsMenu episode={row.original} />
        )}
      </div>
    ),
  },
]
