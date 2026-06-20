// TODO: Validate
import type { ColumnDef } from "@tanstack/react-table"

import type {
  EpisodeOutput,
  PluginOutput,
  SeasonOutput,
  ShowPublic,
  SourcePublic,
  WatchItem,
} from "@/client"
import { CopyId } from "@/components/Common/CopyId"
import { cn } from "@/lib/utils"
import { WatchActionsMenu } from "./WatchActionsMenu"

export interface WatchWithDetails extends WatchItem {
  episode: EpisodeOutput
  season: SeasonOutput
  show: ShowPublic
  source: SourcePublic
  plugin: PluginOutput
  pending?: boolean
}

export const columns: ColumnDef<WatchWithDetails>[] = [
  {
    accessorKey: "id",
    header: "ID",
    cell: ({ row }) => <CopyId id={row.original.id} />,
  },

  {
    accessorFn: (row) => row.show.name,
    id: "plugin",
    header: "Plugin",
    cell: ({ row }) => (
      <span className="font-medium">{row.original.plugin.name ?? ""}</span>
    ),
  },

  {
    accessorKey: "source.name",
    header: "Source",
    cell: ({ row }) => {
      const { source } = row.original
      return (
        // flex - Image and text on the same line
        // items-center - Vertically center the image
        // gap-2 - Small space between image and text
        <div className="flex items-center gap-2">
          {source.favicon_url && (
            <img
              src={source.favicon_url}
              alt={`${source.name} favicon`}
              className="size-4"
            />
          )}
          <span className="text-muted-foreground">{source.name ?? ""}</span>
        </div>
      )
    },
  },

  {
    accessorFn: (row) => row.show.name,
    id: "show",
    header: "Show",
    cell: ({ row }) => {
      const { show } = row.original
      const name = show.name ?? ""
      if (show.url) {
        return (
          <a
            href={show.url}
            target="_blank"
            rel="noopener noreferrer"
            className="font-medium text-primary hover:underline"
          >
            {name}
          </a>
        )
      }
      return <span className="font-medium">{name}</span>
    },
  },
  {
    accessorFn: (row) =>
      `${row.season.season_number ?? ""} ${row.season.name ?? ""}`.trim(),
    id: "season",
    header: "Season",
    cell: ({ row }) => {
      const { season } = row.original
      const label = `${season.season_number ?? ""} ${season.name ?? ""}`.trim()
      if (season.url) {
        return (
          <a
            href={season.url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-primary hover:underline"
          >
            {label}
          </a>
        )
      }
      return <span>{label}</span>
    },
  },
  {
    accessorFn: (row) =>
      `${row.episode.episode_number ?? ""} ${row.episode.name ?? ""}`.trim(),
    id: "episode",
    header: "Episode",
    cell: ({ row }) => {
      const { episode } = row.original
      const label =
        `${episode.episode_number ?? ""} ${episode.name ?? ""}`.trim()
      if (episode.url) {
        return (
          <a
            href={episode.url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-primary hover:underline"
          >
            {label}
          </a>
        )
      }
      return <span>{label}</span>
    },
  },
  {
    accessorKey: "watch_date",
    header: "Watch Date",
    meta: { filterVariant: "dateRange" },
    cell: ({ row }) => {
      const date = row.original.watch_date
      if (!date)
        return <span className="text-muted-foreground italic">Not set</span>
      return (
        <span>
          {new Date(date).toLocaleDateString()}{" "}
          {new Date(date).toLocaleTimeString()}
        </span>
      )
    },
  },
  {
    accessorFn: (row) => (row.verified ? "Yes" : "No"),
    id: "verified",
    header: "Verified",
    meta: { filterVariant: "select" },
    filterFn: "equalsString",
    cell: ({ row }) => (
      <div className="flex items-center gap-2">
        <span
          className={cn(
            "size-2 rounded-full",
            row.original.verified ? "bg-green-500" : "bg-gray-400",
          )}
        />
        <span className={row.original.verified ? "" : "text-muted-foreground"}>
          {row.original.verified ? "Yes" : "No"}
        </span>
      </div>
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
          <WatchActionsMenu watch={row.original} />
        )}
      </div>
    ),
  },
]
