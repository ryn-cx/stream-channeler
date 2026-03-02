// TODO: Validate
import type { ColumnDef } from "@tanstack/react-table"

import type {
  EpisodeOutput,
  EpisodeWatchItem,
  PluginOutput,
  SeasonOutput,
  ShowOutput,
  SourceOutput,
} from "@/client"
import { CopyId } from "@/components/Common/CopyId"
import { cn } from "@/lib/utils"
import DeleteWatch from "./DeleteWatch"
import EditWatch from "./EditWatch"
import VerifyWatch from "./VerifyWatch"

interface WatchWithDetails extends EpisodeWatchItem {
  episode: EpisodeOutput
  season: SeasonOutput
  show: ShowOutput
  source: SourceOutput
  plugin: PluginOutput
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
    cell: ({ row }) => (
      <span className="font-medium">{row.original.show.name ?? ""}</span>
    ),
  },
  {
    accessorFn: (row) => `${row.season.season_number} ${row.season.name ?? ""}`,
    id: "season",
    header: "Season",
    cell: ({ row }) => (
      <span>
        {row.original.season.season_number} {row.original.season.name ?? ""}
      </span>
    ),
  },
  {
    accessorFn: (row) =>
      `${row.episode.episode_number} ${row.episode.name ?? ""}`,
    id: "episode",
    header: "Episode",
    cell: ({ row }) => (
      <span>
        {row.original.episode.episode_number} {row.original.episode.name ?? ""}
      </span>
    ),
  },
  {
    accessorKey: "watch_date",
    header: "Watch Date",
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
    header: () => <span className="sr-only">Actions</span>,
    cell: ({ row }) => (
      <div className="flex justify-end">
        <VerifyWatch
          id={row.original.id}
          verified={row.original.verified}
          watch_date={row.original.watch_date}
        />
        <EditWatch watch={row.original} />
        <DeleteWatch id={row.original.id} />
      </div>
    ),
  },
]
