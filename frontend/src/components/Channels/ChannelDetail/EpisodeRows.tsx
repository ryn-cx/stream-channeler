// TODO: Validate
import { useQueryClient } from "@tanstack/react-query"

import type { EpisodeWithDetails } from "./columns"
import { EpisodeRow } from "./EpisodeRow"

interface EpisodeRowsProps {
  episodes: EpisodeWithDetails[]
  channelId: string
}

// TODO: Validate
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

  // TODO: Validate
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
    if (!nextEpisode) return
    const anchorEpisodeId = episodes[anchorIndex].id
    const nextEpisodeId = nextEpisode.id

    queryClient.setQueriesData(
      { queryKey: ["episodes", channelId] },
      (oldData: any) => {
        if (!oldData?.episodes) return oldData
        const eps = [...oldData.episodes]
        const nextIndex = eps.findIndex((ep: any) => ep.id === nextEpisodeId)
        const anchorIndexInCache = eps.findIndex(
          (ep: any) => ep.id === anchorEpisodeId,
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
