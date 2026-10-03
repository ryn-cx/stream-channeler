// TODO: Validate
import { useLocation, useRouter } from "@tanstack/react-router"

import type { HeroLink } from "@/components/ChannelCommon/TitleInformationDialog"
import type { EditableEpisodeFields } from "@/components/Episodes/Edit"

export type MediaTarget =
  | { kind: "title"; titleId: string; extraLinks?: HeroLink[] }
  | { kind: "season"; seasonIds: string[] }
  | {
      kind: "episode"
      episode: Pick<EditableEpisodeFields, "id"> &
        Partial<EditableEpisodeFields>
    }

export interface MediaInformationState {
  target: MediaTarget
  depth: number
}

declare module "@tanstack/history" {
  interface HistoryState {
    mediaInformation?: MediaInformationState
  }
}

// TODO: Validate
export function useMediaInformationState() {
  return useLocation({ select: (location) => location.state.mediaInformation })
}

// TODO: Validate
function storedTarget(target: MediaTarget): MediaTarget {
  if (target.kind !== "episode") {
    return target
  }
  const episode = target.episode
  return {
    kind: "episode",
    episode: {
      id: episode.id,
      tmdb_episode_ids: episode.tmdb_episode_ids,
      episode_number: episode.episode_number,
      tmdb_episode_validated_at: episode.tmdb_episode_validated_at,
      tmdb_episode_note: episode.tmdb_episode_note,
    },
  }
}

// TODO: Validate
export function useOpenMedia() {
  const router = useRouter()
  return (target: MediaTarget) => {
    const current = router.history.location.state.mediaInformation
    router.history.push(router.history.location.href, {
      mediaInformation: {
        target: storedTarget(target),
        depth: current ? current.depth + 1 : 0,
      },
    })
  }
}

// TODO: Validate
export function useCloseMedia() {
  const router = useRouter()
  return () => {
    const current = router.history.location.state.mediaInformation
    if (current) {
      router.history.go(-(current.depth + 1))
    }
  }
}
