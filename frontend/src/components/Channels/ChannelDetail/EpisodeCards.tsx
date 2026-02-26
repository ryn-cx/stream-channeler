// TODO: Validate
import { useMutation, useQueryClient } from "@tanstack/react-query"
import {
  BadgeCheck,
  Check,
  ExternalLink,
  ListX,
  MoreVertical,
  SkipForward,
} from "lucide-react"
import { lazy, Suspense, useState } from "react"
import { MediaService } from "@/client"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import useCustomToast from "@/hooks/useCustomToast"
import { useMarkEpisodeWatched } from "@/hooks/useMarkEpisodeWatched"
import { useToggleEpisodeWhitelist } from "@/hooks/useToggleEpisodeWhitelist"
import { handleError } from "@/utils"
import type { EpisodeWithDetails } from "./columns"

interface EpisodeCardsProps {
  episodes: EpisodeWithDetails[]
  channelId: string
}

export function formatDuration(seconds: number): string {
  const hours = Math.floor(seconds / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  const secs = seconds % 60

  if (hours > 0) {
    return `${hours}:${minutes.toString().padStart(2, "0")}:${secs.toString().padStart(2, "0")}`
  }
  return `${minutes}:${secs.toString().padStart(2, "0")}`
}

// Load all card overlay formats from CardOverlays subdirectories
// Pattern: [pluginKey]/[mediaType].tsx
// Example: ryn.cx-YouTube/YouTube Channel.tsx, generic/Movie.tsx
const allModules = import.meta.glob<{ default: React.ComponentType<any> }>(
  "./CardOverlays/*/*.tsx",
  { eager: false },
)

// Create lazy-loaded component maps
const pluginFormats: Record<
  string,
  Record<string, React.LazyExoticComponent<React.ComponentType<any>>>
> = {}

const genericFormats: Record<
  string,
  React.LazyExoticComponent<React.ComponentType<any>>
> = {}

// Process all formats
// Path format: ./CardOverlays/[pluginKey]/[mediaType].tsx
// Example: ./CardOverlays/ryn.cx-YouTube/YouTube Channel.tsx -> plugin: "ryn.cx-YouTube", mediaType: "YouTube Channel"
// Example: ./CardOverlays/generic/Movie.tsx -> generic format for "Movie"
for (const path in allModules) {
  const match = path.match(/^\.\/CardOverlays\/([^/]+)\/(.+?)\.tsx$/)
  if (match) {
    const pluginKey = match[1]
    const mediaType = match[2]

    if (pluginKey === "generic") {
      // Store generic formats separately
      genericFormats[mediaType] = lazy(allModules[path] as any)
    } else {
      // Store plugin-specific formats
      if (!pluginFormats[pluginKey]) {
        pluginFormats[pluginKey] = {}
      }
      pluginFormats[pluginKey][mediaType] = lazy(allModules[path] as any)
    }
  }
}

function EpisodeCardOverlay({ episode }: { episode: EpisodeWithDetails }) {
  const mediaType = episode.show.media_type || ""
  const pluginKey = episode.plugin.key

  let OverlayComponent: React.LazyExoticComponent<
    React.ComponentType<any>
  > | null = null

  // First, try to find plugin-specific format if plugin key is provided
  if (pluginFormats[pluginKey]) {
    OverlayComponent = pluginFormats[pluginKey][mediaType] || null
  }

  // If no plugin-specific format found, fall back to generic format by media type
  if (!OverlayComponent) {
    OverlayComponent = genericFormats[mediaType] || null
  }

  // Ultimate fallback to generic/generic.tsx if it exists
  if (!OverlayComponent) {
    OverlayComponent = genericFormats.generic || null
  }

  return (
    <Suspense fallback={null}>
      {OverlayComponent && (
        <OverlayComponent episode={episode} formatDuration={formatDuration} />
      )}
    </Suspense>
  )
}

function EpisodeCard({
  episode,
  channelId,
  nextEpisodeId,
  onNextEpisode,
}: {
  episode: EpisodeWithDetails
  channelId: string
  nextEpisodeId: string | undefined
  onNextEpisode: (currentEpisodeId: string) => void
}) {
  const [_cardRendered, setCardRendered] = useState(false)
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const watchedMutation = useMarkEpisodeWatched(channelId)
  const whitelistMutation = useToggleEpisodeWhitelist(
    episode.channel_id,
    channelId,
  )

  const queryClient = useQueryClient()
  const verifyMutation = useMutation({
    mutationFn: () =>
      MediaService.patchWatchedEpisode({
        episodeWatchId: episode.episode_watch_id!,
        requestBody: {
          watch_date: episode.watch_date!,
          verified: true,
        },
      }),
    // When mutate is called:
    onMutate: async () => {
      // Cancel any outgoing refetches
      // (so they don't overwrite our optimistic update)
      await queryClient.cancelQueries({ queryKey: ["episodes", channelId] })

      // Snapshot the previous value
      const previous = queryClient.getQueryData(["episodes", channelId])

      // Optimistically update to the new value
      queryClient.setQueryData(["episodes", channelId], (oldData: any) => {
        if (!oldData) return oldData
        return {
          ...oldData,
          episodes: oldData.episodes.map((ep: any) =>
            ep.id === episode.id ? { ...ep, verified: true } : ep,
          ),
        }
      })

      // Return a result with the snapshotted value
      return { previous }
    },
    onSuccess: () => {
      showSuccessToast("Episode verified successfully")
    },
    // If the mutation fails,
    // use the result returned from onMutate to roll back
    onError: (
      error: unknown,
      _vars: undefined,
      context: { previous: unknown } | undefined,
    ) => {
      if (context?.previous) {
        queryClient.setQueryData(["episodes", channelId], context.previous)
      }
      handleError.call(showErrorToast, error as any)
    },
  })

  const handleClick = () => {
    watchedMutation.mutate(episode.id)
    window.open(episode.url, "_blank", "noopener,noreferrer")
  }

  const watched = !!episode.watch_date
  const verified = episode.verified
  const watchDate = episode.watch_date
  const formattedDate = watchDate
    ? new Date(watchDate).toLocaleDateString()
    : ""

  const imageUrl =
    episode.image_url ||
    episode.season.image_url ||
    episode.show.image_url ||
    ""

  return (
    <Card
      // overflow-hidden - Hide anything that goes outside the card
      // cursor-pointer - When hovering over the card make the cursor a pointer so you can
      // tell it is a link
      // hover:-translate-y-0.5 hover:shadow-lg - When hovering over a card make it move
      // a little bit
      // transition-all - Make movement have a smooth animation
      // p-0 - No extra padding
      // bg-card - Give cards a slight background color
      // flex flex-col - Make height of card flexible
      className="group overflow-hidden cursor-pointer hover:bg-accent transition-colors p-0 bg-card no-border rounded-none"
      onClick={handleClick}
    >
      {/* relative - I have no idea but everything breaks without it */}
      {/* flex-shrink-0 - Fit images to the card without stretching */}
      <div className="relative flex-shrink-0">
        <img
          loading="lazy"
          src={imageUrl}
          alt={`Episode ${episode.episode_number} - ${episode.name}`}
          className="object-cover transition-opacity group-hover:opacity-80"
          onLoad={(e) => {
            const img = e.target as HTMLImageElement
            img.style.objectFit = "cover"
            setCardRendered(true)
          }}
        />

        {/* TODO: The colors for this badge are bad */}
        {watched && (
          <Badge
            variant={verified ? "default" : "secondary"}
            className="absolute top-0 left-0 z-10"
          >
            {verified
              ? `Last Watched - ${formattedDate}`
              : `Last Watched - ${formattedDate} (Not Verified)`}
          </Badge>
        )}

        {/* Burger menu in top right corner */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button
              variant="ghost"
              size="icon"
              className="absolute top-2 right-2 z-10 h-8 w-8 bg-background/80 hover:bg-background/90 backdrop-blur-sm"
              onClick={(e) => e.stopPropagation()}
            >
              <MoreVertical className="h-4 w-4" />
              <span className="sr-only">Open menu</span>
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" onClick={(e) => e.stopPropagation()}>
            <DropdownMenuItem
              onClick={(e) => {
                e.stopPropagation()
                watchedMutation.mutate(episode.id)
              }}
            >
              <Check className="h-4 w-4" />
              Mark as Watched
            </DropdownMenuItem>
            {episode.watch_date &&
              !episode.verified &&
              episode.episode_watch_id && (
                <DropdownMenuItem
                  onClick={(e) => {
                    e.stopPropagation()
                    verifyMutation.mutate(undefined)
                  }}
                >
                  <BadgeCheck className="h-4 w-4" />
                  Verify Watch
                </DropdownMenuItem>
              )}
            {nextEpisodeId && (
              <DropdownMenuItem
                onClick={(e) => {
                  e.stopPropagation()
                  onNextEpisode(episode.id)
                }}
              >
                <SkipForward className="h-4 w-4" />
                Next Episode
              </DropdownMenuItem>
            )}
            <DropdownMenuItem
              onClick={(e) => {
                e.stopPropagation()
                const confirmMsg = `Blacklist episode "${episode.name}"?`
                if (window.confirm(confirmMsg)) {
                  whitelistMutation.mutate(episode.id)
                }
              }}
            >
              <ListX className="h-4 w-4" />
              Blacklist Episode
            </DropdownMenuItem>
            <DropdownMenuItem
              onClick={(e) => {
                e.stopPropagation()
                window.open(episode.url, "_blank", "noopener,noreferrer")
              }}
            >
              <ExternalLink className="h-4 w-4" />
              Open URL
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>

      {/* px-2 pb-2 - Border area around the text to make easier to read */}
      <div className="px-2 pb-2">
        <EpisodeCardOverlay episode={episode} />
      </div>
    </Card>
  )
}

export function EpisodeCards({ episodes, channelId }: EpisodeCardsProps) {
  const queryClient = useQueryClient()

  // Build a map of episodeId → next episode ID for the same show
  const nextEpisodeMap = new Map<string, string>()
  const lastSeenByShow = new Map<string, number>()
  for (let i = 0; i < episodes.length; i++) {
    const showId = episodes[i].show.id
    const prevIndex = lastSeenByShow.get(showId)
    if (prevIndex !== undefined) {
      nextEpisodeMap.set(episodes[prevIndex].id, episodes[i].id)
    }
    lastSeenByShow.set(showId, i)
  }

  const handleNextEpisode = (currentEpisodeId: string) => {
    const nextEpisodeId = nextEpisodeMap.get(currentEpisodeId)
    if (!nextEpisodeId) return

    queryClient.setQueryData(["episodes", channelId], (oldData: any) => {
      if (!oldData) return oldData
      const eps = [...oldData.episodes]
      const currentIndex = eps.findIndex(
        (ep: any) => ep.id === currentEpisodeId,
      )
      const nextIndex = eps.findIndex((ep: any) => ep.id === nextEpisodeId)
      if (currentIndex === -1 || nextIndex === -1) return oldData

      // Remove the next episode from its current position
      const [nextEp] = eps.splice(nextIndex, 1)
      // Insert after the current episode (adjust index if next was before current)
      const insertAt =
        nextIndex < currentIndex ? currentIndex : currentIndex + 1
      eps.splice(insertAt, 0, nextEp)

      return { ...oldData, episodes: eps }
    })
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5 3xl:grid-cols-6 4xl:grid-cols-7 5xl:grid-cols-8 gap-4 items-start">
      {episodes.map((episode) => (
        <EpisodeCard
          key={episode.id}
          episode={episode}
          channelId={channelId}
          nextEpisodeId={nextEpisodeMap.get(episode.id)}
          onNextEpisode={handleNextEpisode}
        />
      ))}
    </div>
  )
}
