// TODO: Validate
import { useMutation, useQueryClient } from "@tanstack/react-query"
import {
  BadgeCheck,
  Check,
  ExternalLink,
  ListX,
  MoreVertical,
  Play,
  SkipForward,
} from "lucide-react"
import { lazy, Suspense, useState } from "react"
import { WatchesService } from "@/client"
import { ConfirmDialog } from "@/components/Common/ConfirmDialog"
import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import useCustomToast from "@/hooks/useCustomToast"
import { useMarkWatched } from "@/hooks/useMarkEpisodeWatched"
import { useToggleEpisodeWhitelist } from "@/hooks/useToggleEpisodeWhitelist"
import { cn } from "@/lib/utils"
import { handleError } from "@/utils"
import type { EpisodeWithDetails } from "./columns"
import { formatDuration } from "./EpisodeCards"

// Reuse card overlay system from EpisodeCards
const allModules = import.meta.glob<{ default: React.ComponentType<any> }>(
  "./CardOverlays/*/*.tsx",
  { eager: false },
)

const pluginFormats: Record<
  string,
  Record<string, React.LazyExoticComponent<React.ComponentType<any>>>
> = {}
const genericFormats: Record<
  string,
  React.LazyExoticComponent<React.ComponentType<any>>
> = {}

for (const path in allModules) {
  const match = path.match(/^\.\/CardOverlays\/([^/]+)\/(.+?)\.tsx$/)
  if (match) {
    const pluginKey = match[1]
    const mediaType = match[2]
    if (pluginKey === "generic") {
      genericFormats[mediaType] = lazy(allModules[path] as any)
    } else {
      if (!pluginFormats[pluginKey]) pluginFormats[pluginKey] = {}
      pluginFormats[pluginKey][mediaType] = lazy(allModules[path] as any)
    }
  }
}

function TileOverlay({ episode }: { episode: EpisodeWithDetails }) {
  const mediaType = episode.show.media_type || ""
  const pluginKey = episode.plugin.key

  let OverlayComponent: React.LazyExoticComponent<
    React.ComponentType<any>
  > | null = null
  if (pluginFormats[pluginKey]) {
    OverlayComponent = pluginFormats[pluginKey][mediaType] || null
  }
  if (!OverlayComponent) {
    OverlayComponent = genericFormats[mediaType] || null
  }
  if (!OverlayComponent) {
    OverlayComponent = genericFormats.generic || null
  }

  return (
    <Suspense fallback={null}>
      {OverlayComponent && <OverlayComponent episode={episode} />}
    </Suspense>
  )
}

interface EpisodeTileProps {
  episode: EpisodeWithDetails
  channelId: string
  nextEpisodeId: string | undefined
  onNextEpisode: (currentEpisodeId: string) => void
}

export function EpisodeTile({
  episode,
  channelId,
  nextEpisodeId,
  onNextEpisode,
}: EpisodeTileProps) {
  const [hovered, setHovered] = useState(false)
  const [confirmBlacklist, setConfirmBlacklist] = useState(false)
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const watchedMutation = useMarkWatched(channelId)
  const whitelistMutation = useToggleEpisodeWhitelist(
    episode.channel_id,
    channelId,
  )
  const queryClient = useQueryClient()

  const verifyMutation = useMutation({
    mutationFn: () =>
      WatchesService.updateUserWatch({
        watchId: episode.episode_watch_id!,
        requestBody: {
          watch_date: episode.watch_date!,
          verified: true,
        },
      }),
    onMutate: async () => {
      await queryClient.cancelQueries({ queryKey: ["episodes", channelId] })
      const previousEntries = queryClient.getQueriesData({
        queryKey: ["episodes", channelId],
      })
      queryClient.setQueriesData(
        { queryKey: ["episodes", channelId] },
        (oldData: any) => {
          if (!oldData) return oldData
          return {
            ...oldData,
            episodes: oldData.episodes.map((ep: any) =>
              ep.id === episode.id ? { ...ep, verified: true } : ep,
            ),
          }
        },
      )
      return { previousEntries }
    },
    onSuccess: () => showSuccessToast("Episode verified successfully"),
    onError: (
      error: unknown,
      _vars: undefined,
      context: { previousEntries: [unknown, unknown][] } | undefined,
    ) => {
      for (const [queryKey, data] of context?.previousEntries ?? []) {
        queryClient.setQueryData(queryKey as any, data)
      }
      handleError.call(showErrorToast, error as any)
    },
  })

  const handlePlay = () => {
    watchedMutation.mutate(episode.id)
    if (episode.url) {
      window.open(episode.url, "_blank", "noopener,noreferrer")
    }
  }

  const watched = !!episode.watch_date
  const imageUrl =
    episode.image_url ||
    episode.season.image_url ||
    episode.show.image_url ||
    ""

  return (
    <>
      {/* biome-ignore lint/a11y/noStaticElementInteractions: hover tracking only, not interactive */}
      <div
        className="relative shrink-0 w-[200px] md:w-[250px] lg:w-[280px] scroll-snap-align-start group/tile"
        onMouseEnter={() => setHovered(true)}
        onMouseLeave={() => setHovered(false)}
      >
        {/* Main tile */}
        <div
          className={cn(
            "relative rounded-sm overflow-hidden cursor-pointer transition-all duration-300 ease-in-out",
            hovered && "scale-110 z-30 shadow-2xl shadow-black/80",
          )}
        >
          {/* Thumbnail */}
          <div className="relative aspect-video bg-zinc-900">
            {imageUrl && (
              <img
                loading="lazy"
                src={imageUrl}
                alt={episode.name ?? ""}
                className="w-full h-full object-cover"
              />
            )}

            {/* Watched progress bar */}
            {watched && (
              <div className="absolute bottom-0 left-0 right-0 h-1 bg-zinc-700">
                <div
                  className={cn(
                    "h-full",
                    episode.verified ? "bg-primary" : "bg-yellow-500",
                  )}
                  style={{ width: "100%" }}
                />
              </div>
            )}

            {/* Play icon on hover */}
            {hovered && (
              <button
                type="button"
                className="absolute inset-0 flex items-center justify-center bg-black/20 border-none p-0 cursor-pointer"
                onClick={handlePlay}
              >
                <div className="rounded-full bg-white/90 p-2">
                  <Play className="size-6 text-black fill-black" />
                </div>
              </button>
            )}
          </div>

          {/* Expanded info panel on hover */}
          {hovered && (
            <div className="bg-zinc-800 p-3 flex flex-col gap-2">
              {/* Action buttons row */}
              <div className="flex items-center gap-1">
                <Button
                  variant="outline"
                  size="icon"
                  className="size-8 rounded-full border-zinc-500 bg-transparent hover:border-white"
                  onClick={(e) => {
                    e.stopPropagation()
                    watchedMutation.mutate(episode.id)
                  }}
                  title="Mark as Watched"
                >
                  <Check className="size-4" />
                </Button>

                {episode.watch_date &&
                  !episode.verified &&
                  episode.episode_watch_id && (
                    <Button
                      variant="outline"
                      size="icon"
                      className="size-8 rounded-full border-zinc-500 bg-transparent hover:border-white"
                      onClick={(e) => {
                        e.stopPropagation()
                        verifyMutation.mutate(undefined)
                      }}
                      title="Verify Watch"
                    >
                      <BadgeCheck className="size-4" />
                    </Button>
                  )}

                {nextEpisodeId && (
                  <Button
                    variant="outline"
                    size="icon"
                    className="size-8 rounded-full border-zinc-500 bg-transparent hover:border-white"
                    onClick={(e) => {
                      e.stopPropagation()
                      onNextEpisode(episode.id)
                    }}
                    title="Next Episode"
                  >
                    <SkipForward className="size-4" />
                  </Button>
                )}

                <div className="ml-auto">
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <Button
                        variant="outline"
                        size="icon"
                        className="size-8 rounded-full border-zinc-500 bg-transparent hover:border-white"
                        onClick={(e) => e.stopPropagation()}
                      >
                        <MoreVertical className="size-4" />
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent
                      align="end"
                      onClick={(e) => e.stopPropagation()}
                    >
                      <DropdownMenuItem
                        onClick={() => setConfirmBlacklist(true)}
                      >
                        <ListX className="size-4" />
                        Blacklist Episode
                      </DropdownMenuItem>
                      {episode.url && (
                        <DropdownMenuItem
                          onClick={() =>
                            window.open(
                              episode.url!,
                              "_blank",
                              "noopener,noreferrer",
                            )
                          }
                        >
                          <ExternalLink className="size-4" />
                          Open URL
                        </DropdownMenuItem>
                      )}
                    </DropdownMenuContent>
                  </DropdownMenu>
                </div>
              </div>

              {/* Episode info */}
              <div className="text-xs text-zinc-400 flex items-center gap-2">
                {episode.duration != null && episode.duration > 0 && (
                  <span>{formatDuration(episode.duration)}</span>
                )}
                {episode.air_date && (
                  <span>{new Date(episode.air_date).toLocaleDateString()}</span>
                )}
              </div>

              {/* Card overlay content */}
              <div className="text-xs">
                <TileOverlay episode={episode} />
              </div>
            </div>
          )}
        </div>

        {/* Title below tile (always visible) */}
        {!hovered && (
          <div className="mt-1 px-0.5">
            <p className="text-xs text-muted-foreground truncate">
              {episode.name || `Episode ${episode.episode_number || ""}`}
            </p>
          </div>
        )}
      </div>

      {confirmBlacklist && (
        <ConfirmDialog
          open={confirmBlacklist}
          onOpenChange={setConfirmBlacklist}
          title="Blacklist Episode"
          description={`Are you sure you want to blacklist "${episode.name ?? ""}"? This episode will be hidden from this channel.`}
          confirmLabel="Blacklist"
          onConfirm={() =>
            whitelistMutation.mutate({
              episodeId: episode.id,
              showId: episode.show.id,
            })
          }
        />
      )}
    </>
  )
}
