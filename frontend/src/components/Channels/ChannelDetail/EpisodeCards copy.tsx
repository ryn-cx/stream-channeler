// TODO: Validate
import { useMutation, useQueryClient } from "@tanstack/react-query"
import {
  BadgeCheck,
  Check,
  ExternalLink,
  EyeOff,
  ListX,
  Radio,
  SkipForward,
  Trash2,
} from "lucide-react"
import { useRef, useState } from "react"
import { type ChannelEpisodesOutput, WatchesService } from "@/client"
import { ConfirmDialog } from "@/components/Common/ConfirmDialog"
import type { ActionMenuItem } from "@/components/Common/ResponsiveActionMenu"
import {
  type MoveDirection,
  EpisodeCard as SharedEpisodeCard,
} from "@/components/PlaylistChannelCommon/EpisodeCard"
import {
  EPISODE_GRID_CLASSES,
  resolveArrowMove,
  useColumnCount,
} from "@/components/PlaylistChannelCommon/episodeGrid"
import { Badge } from "@/components/ui/badge"
import useCustomToast from "@/hooks/useCustomToast"
import { useMarkWatched } from "@/hooks/useMarkEpisodeWatched"
import { useToggleEpisodeWhitelist } from "@/hooks/useToggleEpisodeWhitelist"
import { cn } from "@/lib/utils"
import { handleError } from "@/utils"
import type { EpisodeWithDetails } from "./columns"

interface EpisodeCardsProps {
  episodes: EpisodeWithDetails[]
  channelId: string
  hideWatched?: boolean
  editOrder?: boolean
}

export function EpisodeCard({
  episode,
  channelId,
  nextEpisodeId,
  onNextEpisode,
  onHide,
  hideWatched,
  editOrder,
  onMove,
  onDrop,
  index,
}: {
  episode: EpisodeWithDetails
  channelId: string
  nextEpisodeId?: string | undefined
  onNextEpisode?: (currentEpisodeId: string) => void
  onHide?: (episodeId: string) => void
  hideWatched?: boolean
  editOrder?: boolean
  onMove?: (index: number, direction: MoveDirection) => void
  onDrop?: (fromIndex: number, toIndex: number) => void
  index?: number
}) {
  const [confirmBlacklist, setConfirmBlacklist] = useState(false)
  const [confirmDeleteWatch, setConfirmDeleteWatch] = useState(false)
  const [confirmWatch, setConfirmWatch] = useState(false)
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const watchedMutation = useMarkWatched(channelId)
  const whitelistMutation = useToggleEpisodeWhitelist(
    episode.channel_id,
    channelId,
  )

  const queryClient = useQueryClient()
  const verifyMutation = useMutation({
    mutationFn: (variables: { watchId: string; watchDate: string }) =>
      WatchesService.updateWatch({
        watchId: variables.watchId,
        requestBody: {
          watch_date: variables.watchDate,
          verified: true,
        },
      }),
    onMutate: async () => {
      await queryClient.cancelQueries({ queryKey: ["episodes", channelId] })
      const previousEntries = queryClient.getQueriesData({
        queryKey: ["episodes", channelId],
      })
      queryClient.setQueriesData<ChannelEpisodesOutput>(
        { queryKey: ["episodes", channelId] },
        (oldData) => {
          if (!oldData) return oldData
          if (hideWatched) {
            return {
              ...oldData,
              episodes: oldData.episodes.filter((ep) => ep.id !== episode.id),
            }
          }
          return {
            ...oldData,
            episodes: oldData.episodes.map((ep) =>
              ep.id === episode.id ? { ...ep, verified: true } : ep,
            ),
          }
        },
      )
      return { previousEntries }
    },
    onSuccess: () => {
      showSuccessToast("Episode verified successfully")
    },
    onError: (
      error: unknown,
      _variables: { watchId: string; watchDate: string },
      context: { previousEntries: [unknown, unknown][] } | undefined,
    ) => {
      for (const [queryKey, data] of context?.previousEntries ?? []) {
        queryClient.setQueryData(queryKey as any, data)
      }
      handleError.call(showErrorToast, error as any)
    },
  })

  const deleteWatchMutation = useMutation({
    mutationFn: () =>
      WatchesService.deleteWatch({
        watchId: episode.episode_watch_id!,
      }),
    onMutate: async () => {
      await queryClient.cancelQueries({ queryKey: ["episodes", channelId] })
      const previousEntries = queryClient.getQueriesData({
        queryKey: ["episodes", channelId],
      })
      const clearWatch = (
        oldData: ChannelEpisodesOutput | undefined,
      ): ChannelEpisodesOutput | undefined => {
        if (!oldData) return oldData
        return {
          ...oldData,
          episodes: oldData.episodes.map((ep) =>
            ep.id === episode.id
              ? {
                  ...ep,
                  watch_date: null,
                  verified: null,
                  episode_watch_id: null,
                }
              : ep,
          ),
        }
      }
      queryClient.setQueriesData<ChannelEpisodesOutput>(
        { queryKey: ["episodes", channelId] },
        clearWatch,
      )
      queryClient.setQueriesData<ChannelEpisodesOutput>(
        { queryKey: ["episodes-preview", channelId] },
        clearWatch,
      )
      return { previousEntries }
    },
    onSuccess: () => showSuccessToast("Watch deleted successfully"),
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

  const onCardClick = () => {
    // Open the episode and mark it watched; the modal then lets the user verify.
    if (episode.url) {
      window.open(episode.url, "_blank", "noopener,noreferrer")
    }
    watchedMutation.mutate(episode.id)
    setConfirmWatch(true)
  }

  const onConfirmWatch = () => {
    if (episode.episode_watch_id && episode.watch_date) {
      verifyMutation.mutate({
        watchId: episode.episode_watch_id,
        watchDate: episode.watch_date,
      })
    }
  }

  const watched = !!episode.watch_date
  const verified = episode.verified
  const watchDate = episode.watch_date
  const formattedDate = watchDate
    ? new Date(watchDate).toLocaleDateString()
    : ""

  const watchDialogTitle =
    episode.name || `Episode ${episode.episode_number ?? ""}`.trim()
  const watchDialogImageUrl =
    episode.image_url ||
    episode.season.image_url ||
    episode.show.image_url ||
    ""
  const watchStatusText = !watched
    ? "Unwatched"
    : verified
      ? `Watched (${formattedDate})`
      : `Watched - Not Verified (${formattedDate})`

  const topLeftBadge = watched ? (
    <Badge variant={verified ? "default" : "secondary"}>
      {verified
        ? `Last Watched - ${formattedDate}`
        : `Last Watched - ${formattedDate} (Not Verified)`}
    </Badge>
  ) : null

  const menuItems: ActionMenuItem[] = []
  if (episode.watch_date && !episode.verified && episode.episode_watch_id) {
    const watchId = episode.episode_watch_id
    const watchDate = episode.watch_date
    menuItems.push({
      key: "verify",
      icon: <BadgeCheck />,
      label: "Verify Watch",
      onClick: (event) => {
        event.stopPropagation()
        verifyMutation.mutate({ watchId, watchDate })
      },
    })
  } else {
    menuItems.push({
      key: "watched",
      icon: <Check />,
      label: "Mark as Watched",
      onClick: (event) => {
        event.stopPropagation()
        watchedMutation.mutate(episode.id)
      },
    })
  }
  if (nextEpisodeId) {
    menuItems.push({
      key: "next",
      icon: <SkipForward />,
      label: "Next Episode",
      onClick: (event) => {
        event.stopPropagation()
        onNextEpisode?.(episode.id)
      },
    })
  }
  if (episode.watch_date && episode.episode_watch_id) {
    menuItems.push({
      key: "delete-watch",
      icon: <Trash2 />,
      label: "Delete Last Watch",
      onClick: (event) => {
        event.stopPropagation()
        setConfirmDeleteWatch(true)
      },
    })
  }
  menuItems.push({
    key: "hide",
    icon: <EyeOff />,
    label: "Temporarily Hide",
    onClick: (event) => {
      event.stopPropagation()
      onHide?.(episode.id)
    },
  })
  menuItems.push({
    key: "blacklist",
    icon: <ListX />,
    label: "Blacklist Episode",
    onClick: (event) => {
      event.stopPropagation()
      setConfirmBlacklist(true)
    },
  })
  menuItems.push({
    key: "open-url",
    icon: <ExternalLink />,
    label: "Open URL",
    onClick: (event) => {
      event.stopPropagation()
      if (episode.url) {
        window.open(episode.url, "_blank", "noopener,noreferrer")
      }
    },
  })
  menuItems.push({
    key: "go-to-channel",
    icon: <Radio />,
    label: `Go to Channel ${
      episode.channel.channel_number != null
        ? `${episode.channel.channel_number}. `
        : ""
    }${episode.channel.name ?? ""}`,
    to: "/channels/$channelId",
    params: { channelId: episode.channel_id },
    onClick: (event) => event.stopPropagation(),
  })

  return (
    <>
      <SharedEpisodeCard
        episode={episode}
        menuItems={menuItems}
        topLeftBadge={topLeftBadge}
        onClick={onCardClick}
        editOrder={editOrder}
        index={index}
        onMove={onMove}
        onDrop={onDrop}
      />

      {confirmWatch && (
        <ConfirmDialog
          open={confirmWatch}
          onOpenChange={setConfirmWatch}
          title={watchDialogTitle}
          variant="default"
          confirmLabel="Yes"
          cancelLabel="No"
          onConfirm={onConfirmWatch}
          // Inline-only content: DialogDescription renders a <p>, so use spans.
          description={
            <span className="flex flex-col gap-3">
              <span>Did you finish watching this episode?</span>
              {watchDialogImageUrl && (
                <img
                  src={watchDialogImageUrl}
                  alt={watchDialogTitle}
                  className="aspect-video w-full rounded-md object-cover"
                />
              )}
              <span className="flex justify-between gap-4">
                <span className="shrink-0">Status</span>
                <span className="flex items-center gap-2 text-right">
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
                  {watchStatusText}
                </span>
              </span>
            </span>
          }
        />
      )}

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
      {confirmDeleteWatch && (
        <ConfirmDialog
          open={confirmDeleteWatch}
          onOpenChange={setConfirmDeleteWatch}
          title="Delete Last Watch"
          description={`Are you sure you want to delete the last watch for "${episode.name ?? ""}"? This will mark the episode as unwatched.`}
          confirmLabel="Delete"
          onConfirm={() => deleteWatchMutation.mutate(undefined)}
        />
      )}
    </>
  )
}

export function EpisodeCards({
  episodes,
  channelId,
  hideWatched,
  editOrder,
}: EpisodeCardsProps) {
  const queryClient = useQueryClient()
  const { showErrorToast } = useCustomToast()
  const gridRef = useRef<HTMLDivElement>(null)
  const columnCount = useColumnCount(gridRef)

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

  const handleHide = (episodeId: string) => {
    queryClient.setQueriesData<ChannelEpisodesOutput>(
      { queryKey: ["episodes", channelId] },
      (oldData) => {
        if (!oldData) return oldData
        return {
          ...oldData,
          episodes: oldData.episodes.filter((ep) => ep.id !== episodeId),
        }
      },
    )
  }

  const handleNextEpisode = (currentEpisodeId: string) => {
    const nextEpisodeId = nextEpisodeMap.get(currentEpisodeId)
    if (!nextEpisodeId) return

    let anyUpdated = false
    queryClient.setQueriesData<ChannelEpisodesOutput>(
      { queryKey: ["episodes", channelId] },
      (oldData) => {
        if (!oldData?.episodes) return oldData
        const eps: EpisodeWithDetails[] = [
          ...(oldData.episodes as EpisodeWithDetails[]),
        ]
        const currentIndex = eps.findIndex((ep) => ep.id === currentEpisodeId)
        const nextIndex = eps.findIndex((ep) => ep.id === nextEpisodeId)

        const [nextEp] = eps.splice(nextIndex, 1)
        const insertAt =
          nextIndex < currentIndex ? currentIndex : currentIndex + 1
        eps.splice(insertAt, 0, nextEp)

        anyUpdated = true
        return { ...oldData, episodes: eps }
      },
    )

    if (!anyUpdated) {
      showErrorToast("Couldn't find the next episode in the current list")
    }
  }

  const swapEpisodes = (fromIndex: number, toIndex: number) => {
    if (fromIndex === toIndex) return
    queryClient.setQueriesData<ChannelEpisodesOutput>(
      { queryKey: ["episodes", channelId] },
      (oldData) => {
        if (!oldData?.episodes) return oldData
        const eps: EpisodeWithDetails[] = [
          ...(oldData.episodes as EpisodeWithDetails[]),
        ]
        if (
          fromIndex < 0 ||
          toIndex < 0 ||
          fromIndex >= eps.length ||
          toIndex >= eps.length
        ) {
          return oldData
        }
        ;[eps[fromIndex], eps[toIndex]] = [eps[toIndex], eps[fromIndex]]
        return { ...oldData, episodes: eps }
      },
    )
  }

  const moveEpisode = (fromIndex: number, toIndex: number) => {
    if (fromIndex === toIndex) return
    queryClient.setQueriesData<ChannelEpisodesOutput>(
      { queryKey: ["episodes", channelId] },
      (oldData) => {
        if (!oldData?.episodes) return oldData
        const eps: EpisodeWithDetails[] = [
          ...(oldData.episodes as EpisodeWithDetails[]),
        ]
        if (
          fromIndex < 0 ||
          toIndex < 0 ||
          fromIndex >= eps.length ||
          toIndex >= eps.length
        ) {
          return oldData
        }
        const [moved] = eps.splice(fromIndex, 1)
        eps.splice(toIndex, 0, moved)
        return { ...oldData, episodes: eps }
      },
    )
  }

  const handleArrowMove = (index: number, direction: MoveDirection) => {
    const move = resolveArrowMove(
      index,
      direction,
      columnCount,
      episodes.length,
    )
    if (move.kind === "noop") return
    if (move.kind === "move") moveEpisode(index, move.to)
    else swapEpisodes(index, move.to)
  }

  return (
    <div ref={gridRef} className={EPISODE_GRID_CLASSES}>
      {episodes.map((episode, index) => (
        <EpisodeCard
          key={episode.id}
          episode={episode}
          channelId={channelId}
          nextEpisodeId={nextEpisodeMap.get(episode.id)}
          onNextEpisode={handleNextEpisode}
          onHide={handleHide}
          hideWatched={hideWatched}
          editOrder={editOrder}
          onMove={handleArrowMove}
          onDrop={moveEpisode}
          index={index}
        />
      ))}
    </div>
  )
}
