// TODO: Validate
import { useQueryClient } from "@tanstack/react-query"

import type { EpisodeWithDetails } from "./columns"
import { EpisodeRow } from "./EpisodeRow"

interface EpisodeRowsProps {
  episodes: EpisodeWithDetails[]
  channelId: string
}

export function EpisodeRows({ episodes, channelId }: EpisodeRowsProps) {
  const queryClient = useQueryClient()

  // Build next episode map (same logic as EpisodeCards)
  const nextEpisodeMap = new Map<string, string>()
  const lastSeenByShow = new Map<string, number>()
  for (let index = 0; index < episodes.length; index++) {
    const showId = episodes[index].show.id
    const prevIndex = lastSeenByShow.get(showId)
    if (prevIndex !== undefined) {
      nextEpisodeMap.set(episodes[prevIndex].id, episodes[index].id)
    }
    lastSeenByShow.set(showId, index)
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

      const [nextEp] = eps.splice(nextIndex, 1)
      const insertAt =
        nextIndex < currentIndex ? currentIndex : currentIndex + 1
      eps.splice(insertAt, 0, nextEp)

      return { ...oldData, episodes: eps }
    })
  }

  // Group episodes by show, preserving order of first appearance
  const showGroups: Map<
    string,
    { showName: string; episodes: EpisodeWithDetails[] }
  > = new Map()

  for (const episode of episodes) {
    const showId = episode.show.id
    if (!showGroups.has(showId)) {
      showGroups.set(showId, {
        showName: episode.show.name || "Unknown",
        episodes: [],
      })
    }
    showGroups.get(showId)!.episodes.push(episode)
  }

  return (
    <div className="flex flex-col gap-8 pb-8">
      {[...showGroups.entries()].map(([showId, group]) => (
        <EpisodeRow
          key={showId}
          title={group.showName}
          episodes={group.episodes}
          channelId={channelId}
          nextEpisodeMap={nextEpisodeMap}
          onNextEpisode={handleNextEpisode}
        />
      ))}
    </div>
  )
}
