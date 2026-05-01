// TODO: Validate
import { useParams } from "@tanstack/react-router"
import type { ColumnDef } from "@tanstack/react-table"

import type {
  ChannelOutput,
  EpisodeWithDetails as EpisodeWithDetailsOutput,
  PluginOutput,
  SeasonOutput,
  ShowPublic,
  SourcePublic,
} from "@/client"
import { CopyId } from "@/components/Common/CopyId"
import { useMarkWatched } from "@/hooks/useMarkEpisodeWatched"
import { cn } from "@/lib/utils"

export type EpisodeWithDetails = EpisodeWithDetailsOutput & {
  season: SeasonOutput
  show: ShowPublic
  source: SourcePublic
  plugin: PluginOutput
  channel: ChannelOutput
}

function EpisodeLink({ episode }: { episode: EpisodeWithDetails }) {
  const { channelId } = useParams({ strict: false })
  const mutation = useMarkWatched(channelId)

  const handleClick = (e: React.MouseEvent<HTMLAnchorElement>) => {
    e.preventDefault()
    mutation.mutate(episode.id)
    if (episode.url) {
      window.open(episode.url, "_blank", "noopener,noreferrer")
    }
  }

  const label = `${episode.episode_number !== null ? `${episode.episode_number}. ` : ""}${episode.name ?? ""}`

  if (!episode.url) {
    return <span>{label}</span>
  }

  return (
    <a
      href={episode.url}
      onClick={handleClick}
      className="hover:underline text-primary"
      target="_blank"
      // noopener/noreferrer - Don't let the source know the origin of the link
      rel="noopener noreferrer"
    >
      {label}
    </a>
  )
}

export const columns: ColumnDef<EpisodeWithDetails>[] = [
  {
    accessorKey: "id",
    header: "ID",
    cell: ({ row }) => <CopyId id={row.original.id} />,
  },

  {
    accessorKey: "plugin.name",
    header: "Plugin",
    id: "plugin",
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
    accessorKey: "show.name",
    header: "Show",
  },

  {
    id: "season",
    accessorFn: (row) =>
      row.season.name || `Season ${row.season.season_number || "Unknown"}`,
    header: "Season",
  },

  {
    accessorKey: "name",
    header: "Episode",
    cell: ({ row }) => <EpisodeLink episode={row.original} />,
  },

  {
    accessorKey: "air_date",
    header: "Air Date",
    cell: ({ row }) => {
      const airDate = row.original.air_date
      return airDate ? (
        <span>{new Date(airDate).toLocaleDateString()}</span>
      ) : (
        <span className="text-muted-foreground italic">Unknown</span>
      )
    },
    // This filtering is done server side so this is redundant. In addition adding the
    // filters to the top of the table make the air date column too take up extra width.
    enableColumnFilter: false,
  },
  {
    accessorKey: "duration",
    header: "Duration",
    cell: ({ row }) => {
      const duration = row.original.duration
      if (!duration) {
        return <span className="text-muted-foreground italic">Unknown</span>
      }
      const hours = Math.floor(duration / 3600)
      const minutes = Math.floor((duration % 3600) / 60)
      const seconds = duration % 60

      if (hours > 0) {
        return (
          <span>
            {hours}:{minutes.toString().padStart(2, "0")}:
            {seconds.toString().padStart(2, "0")}
          </span>
        )
      }
      return (
        <span>
          {minutes}:{seconds.toString().padStart(2, "0")}
        </span>
      )
    },
    // This filtering is done server side so this is redundant. In addition adding the
    // filters to the top of the table make the duration column too take up extra width.
    enableColumnFilter: false,
  },
  {
    id: "status",
    accessorFn: (row) => {
      const watched = !!row.watch_date
      const verified = row.verified
      const watchDate = row.watch_date

      if (!watched) return "Unwatched"

      const formattedDate = watchDate
        ? new Date(watchDate).toLocaleDateString()
        : ""

      if (verified) return `Watched (${formattedDate})`
      return `Watched (Not Verified) (${formattedDate})`
    },
    header: "Status",
    filterFn: "equalsString",
    cell: ({ row }) => {
      const watched = !!row.original.watch_date
      const verified = row.original.verified
      const watchDate = row.original.watch_date

      const formattedDate = watchDate
        ? new Date(watchDate).toLocaleDateString()
        : ""

      return (
        <div className="flex items-center gap-2">
          <span
            className={cn(
              "size-2 rounded-full",
              watched
                ? verified
                  ? "bg-green-500"
                  : "bg-orange-500"
                : "bg-gray-400",
            )}
          />
          <span className={watched ? "" : "text-muted-foreground"}>
            {!watched && "Unwatched"}
            {watched && verified && "Watched"}
            {watched && !verified && "Watched (Not Verified)"}
          </span>
          {watched && (
            <span className="text-muted-foreground">({formattedDate})</span>
          )}
        </div>
      )
    },
  },
]
