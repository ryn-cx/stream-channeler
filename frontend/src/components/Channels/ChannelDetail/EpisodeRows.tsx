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
  const lastSeenByTitle = new Map<string, number>()
  for (let index = 0; index < episodes.length; index++) {
    const titleId = episodes[index].title.id
    const prevIndex = lastSeenByTitle.get(titleId)
    if (prevIndex !== undefined) {
      nextEpisodeMap.set(episodes[prevIndex].id, episodes[index].id)
    }
    lastSeenByTitle.set(titleId, index)
  }

  // TODO: Validate
  const handleNextEpisode = (currentEpisodeId: string) => {
    const currentIndex = episodes.findIndex((ep) => ep.id === currentEpisodeId)
    if (currentIndex === -1) return
    const titleId = episodes[currentIndex].title.id

    // Walk forward through the run of same-title episodes already queued after
    // the current one so repeated clicks keep extending the chain.
    let anchorIndex = currentIndex
    while (
      anchorIndex + 1 < episodes.length &&
      episodes[anchorIndex + 1].title.id === titleId
    ) {
      anchorIndex++
    }

    const nextEpisode = episodes.find(
      (ep, index) => index > anchorIndex && ep.title.id === titleId,
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

  // Group episodes by title, preserving order of first appearance
  const titleGroups: Map<
    string,
    { titleName: string; episodes: EpisodeWithDetails[] }
  > = new Map()

  for (const episode of episodes) {
    const titleId = episode.title.id
    if (!titleGroups.has(titleId)) {
      titleGroups.set(titleId, {
        titleName: episode.title.name || "Unknown",
        episodes: [],
      })
    }
    titleGroups.get(titleId)!.episodes.push(episode)
  }

  return (
    <div className="flex flex-col gap-8 pb-8">
      {[...titleGroups.entries()].map(([titleId, group]) => (
        <EpisodeRow
          key={titleId}
          title={group.titleName}
          episodes={group.episodes}
          channelId={channelId}
          nextEpisodeMap={nextEpisodeMap}
          onNextEpisode={handleNextEpisode}
        />
      ))}
    </div>
  )
}
