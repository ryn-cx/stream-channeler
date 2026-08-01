// TODO: Validate
import { useQueryClient } from "@tanstack/react-query"
import { useRef, useState } from "react"
import type { ChannelEpisodesOutput } from "@/client"
import {
  type MoveDirection,
  EpisodeCard as SharedEpisodeCard,
} from "@/components/ChannelCommon/EpisodeCard"
import {
  EPISODE_GRID_CLASSES,
  resolveArrowMove,
  useColumnCount,
} from "@/components/ChannelCommon/episodeGrid"
import { LastWatchedBadge } from "@/components/ChannelCommon/LastWatchedBadge"
import { useEpisodeActions } from "@/components/ChannelCommon/useEpisodeActions"
import useCustomToast from "@/hooks/useCustomToast"
import type { WatchFilters } from "@/lib/watchFilters"
import type { EpisodeWithDetails } from "./columns"

interface EpisodeCardsProps {
  episodes: EpisodeWithDetails[]
  channelId: string
  watchFilters?: WatchFilters
  editOrder?: boolean
}

export function EpisodeCard({
  episode,
  channelId,
  nextEpisodeId,
  onNextEpisode,
  watchFilters,
  editOrder,
  onMove,
  onDrop,
  index,
}: {
  episode: EpisodeWithDetails
  channelId: string
  nextEpisodeId?: string | undefined
  onNextEpisode?: (currentEpisodeId: string) => void
  watchFilters?: WatchFilters
  editOrder?: boolean
  onMove?: (index: number, direction: MoveDirection) => void
  onDrop?: (fromIndex: number, toIndex: number) => void
  index?: number
}) {
  const [clicked, setClicked] = useState(false)
  const { menuItems, dialogs, watchedMutation } = useEpisodeActions({
    episode,
    channelId,
    nextEpisodeId,
    onNextEpisode,
    watchFilters,
  })

  const onCardClick = () => {
    setClicked(true)
    watchedMutation.mutate(episode.id)
    if (episode.url) {
      window.open(episode.url, "_blank", "noopener,noreferrer")
    }
  }

  const topLeftBadge = episode.watch_date ? (
    <LastWatchedBadge episode={episode} />
  ) : null

  return (
    <>
      <SharedEpisodeCard
        episode={episode}
        menuItems={menuItems}
        topLeftBadge={topLeftBadge}
        onClick={onCardClick}
        dimmed={clicked}
        editOrder={editOrder}
        index={index}
        onMove={onMove}
        onDrop={onDrop}
      />

      {dialogs}
    </>
  )
}

export function EpisodeCards({
  episodes,
  channelId,
  watchFilters,
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
          watchFilters={watchFilters}
          editOrder={editOrder}
          onMove={handleArrowMove}
          onDrop={moveEpisode}
          index={index}
        />
      ))}
    </div>
  )
}
