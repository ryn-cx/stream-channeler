// TODO: Validate
import { useMutation, useQueryClient } from "@tanstack/react-query"
import {
  BadgeCheck,
  Check,
  ExternalLink,
  EyeOff,
  SkipForward,
  Trash2,
} from "lucide-react"
import { useRef, useState } from "react"
import { type ChannelEpisodesOutput, WatchesService } from "@/client"
import {
  type MoveDirection,
  EpisodeCard as SharedEpisodeCard,
} from "@/components/ChannelCommon/EpisodeCard"
import {
  EPISODE_GRID_CLASSES,
  resolveArrowMove,
  useColumnCount,
} from "@/components/ChannelCommon/episodeGrid"
import { ConfirmDialog } from "@/components/Common/ConfirmDialog"
import type { ActionMenuItem } from "@/components/Common/ResponsiveActionMenu"
import { Badge } from "@/components/ui/badge"
import useCustomToast from "@/hooks/useCustomToast"
import { useMarkWatched } from "@/hooks/useMarkEpisodeWatched"
import { handleError } from "@/utils"
import { BlacklistEpisodeDialog } from "./BlacklistEpisodeDialog"
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
  hideWatched?: boolean
  editOrder?: boolean
  onMove?: (index: number, direction: MoveDirection) => void
  onDrop?: (fromIndex: number, toIndex: number) => void
  index?: number
}) {
  const [confirmBlacklist, setConfirmBlacklist] = useState(false)
  const [confirmDeleteWatch, setConfirmDeleteWatch] = useState(false)
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const watchedMutation = useMarkWatched(channelId)

  const queryClient = useQueryClient()
  const verifyMutation = useMutation({
    mutationFn: () =>
      WatchesService.updateWatch({
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
      _vars: undefined,
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
    watchedMutation.mutate(episode.id)
    if (episode.url) {
      window.open(episode.url, "_blank", "noopener,noreferrer")
    }
  }

  const watched = !!episode.watch_date
  const verified = episode.verified
  const watchDate = episode.watch_date
  const formattedDate = watchDate
    ? new Date(watchDate).toLocaleDateString()
    : ""

  const topLeftBadge = watched ? (
    <Badge variant={verified ? "default" : "secondary"}>
      {verified
        ? `Last Watched - ${formattedDate}`
        : `Last Watched - ${formattedDate} (Not Verified)`}
    </Badge>
  ) : null

  const menuItems: ActionMenuItem[] = []
  if (episode.watch_date && !episode.verified && episode.episode_watch_id) {
    menuItems.push({
      key: "verify",
      icon: <BadgeCheck />,
      label: "Verify Watch",
      onClick: (event) => {
        event.stopPropagation()
        verifyMutation.mutate(undefined)
      },
    })
  } else {
    menuItems.push({
      key: "watched",
      icon: <Check />,
      label: "Mark as Watched",
      keepMenuOpen: true,
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
      keepMenuOpen: true,
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
    key: "blacklist",
    icon: <EyeOff />,
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

      {confirmBlacklist && (
        <BlacklistEpisodeDialog
          episode={episode}
          currentChannelId={channelId}
          open={confirmBlacklist}
          onOpenChange={setConfirmBlacklist}
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

  const handleNextEpisode = (currentEpisodeId: string) => {
    const currentIndex = episodes.findIndex((ep) => ep.id === currentEpisodeId)
    if (currentIndex === -1) return
    const showId = episodes[currentIndex].show.id

    // Walk forward through the run of same-show episodes already queued after
    // the current one so repeated clicks keep extending the chain.
    let anchorIndex = currentIndex
    while (
      anchorIndex + 1 < episodes.length &&
      episodes[anchorIndex + 1].show.id === showId
    ) {
      anchorIndex++
    }

    const nextEpisode = episodes.find(
      (ep, index) => index > anchorIndex && ep.show.id === showId,
    )
    if (!nextEpisode) {
      showErrorToast("Couldn't find the next episode in the current list")
      return
    }
    const anchorEpisodeId = episodes[anchorIndex].id
    const nextEpisodeId = nextEpisode.id

    queryClient.setQueriesData<ChannelEpisodesOutput>(
      { queryKey: ["episodes", channelId] },
      (oldData) => {
        if (!oldData?.episodes) return oldData
        const eps = [...oldData.episodes]
        const nextIndex = eps.findIndex((ep) => ep.id === nextEpisodeId)
        const anchorIndexInCache = eps.findIndex(
          (ep) => ep.id === anchorEpisodeId,
        )
        if (nextIndex === -1 || anchorIndexInCache === -1) return oldData

        const [nextEp] = eps.splice(nextIndex, 1)
        const insertAt =
          nextIndex < anchorIndexInCache
            ? anchorIndexInCache
            : anchorIndexInCache + 1
        eps.splice(insertAt, 0, nextEp)

        return { ...oldData, episodes: eps }
      },
    )
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
