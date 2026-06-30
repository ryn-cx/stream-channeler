// TODO: Validate
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { BadgeCheck, Check, ExternalLink, EyeOff, Trash2 } from "lucide-react"
import { useState } from "react"

import { type PlaylistEpisodesOutput, WatchesService } from "@/client"
import { ConfirmDialog } from "@/components/Common/ConfirmDialog"
import type { ActionMenuItem } from "@/components/Common/ResponsiveActionMenu"
import {
  type BaseEpisodeWithDetails,
  EpisodeCard,
  type MoveDirection,
} from "@/components/PlaylistChannelCommon/EpisodeCard"
import { Badge } from "@/components/ui/badge"
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"

type PlaylistEpisode = BaseEpisodeWithDetails & {
  watch_date?: string | null
  verified?: boolean | null
  episode_watch_id?: string | null
}

interface PlaylistEpisodeCardProps {
  episode: PlaylistEpisode
  /** Required for watch-mutation cache invalidation. Omit on previews. */
  playlistId?: string
  /** Called when the user picks "Temporarily Hide". */
  onHide?: (episodeId: string) => void
  editOrder?: boolean
  index?: number
  onMove?: (index: number, direction: MoveDirection) => void
  onDrop?: (fromIndex: number, toIndex: number) => void
}

function updateEpisodeInData(
  oldData: PlaylistEpisodesOutput | undefined,
  episodeId: string,
  patch: Partial<PlaylistEpisode>,
): PlaylistEpisodesOutput | undefined {
  if (!oldData) return oldData
  return {
    ...oldData,
    episodes: oldData.episodes.map((ep) =>
      ep.id === episodeId ? { ...ep, ...patch } : ep,
    ),
  }
}

export function PlaylistEpisodeCard({
  episode,
  playlistId,
  onHide,
  editOrder,
  index,
  onMove,
  onDrop,
}: PlaylistEpisodeCardProps) {
  const { showSuccessToast, showErrorToast, showWarningToast } =
    useCustomToast()
  const queryClient = useQueryClient()
  const [confirmDeleteWatch, setConfirmDeleteWatch] = useState(false)

  const queryKeys = playlistId
    ? [
        ["playlist-episodes", playlistId] as const,
        ["playlist-episodes-preview", playlistId] as const,
      ]
    : []

  const patchCaches = (episodeId: string, patch: Partial<PlaylistEpisode>) => {
    for (const key of queryKeys) {
      queryClient.setQueriesData<PlaylistEpisodesOutput>(
        { queryKey: key },
        (oldData) => updateEpisodeInData(oldData, episodeId, patch),
      )
    }
  }

  const markWatchedMutation = useMutation({
    mutationFn: (episodeId: string) =>
      WatchesService.createWatch({
        episodeId,
        requestBody: {
          watch_date: new Date().toISOString(),
          verified: false,
        },
      }),
    onMutate: async (episodeId) => {
      for (const key of queryKeys) {
        await queryClient.cancelQueries({ queryKey: key })
      }
      const optimisticPatch = {
        watch_date: new Date().toISOString(),
        verified: false,
      }
      patchCaches(episodeId, optimisticPatch)
      return undefined
    },
    onSuccess: (watchResults, episodeId) => {
      const watchData = watchResults.find(
        (watch) => watch.episode_id === episodeId,
      )
      if (watchData) {
        patchCaches(episodeId, {
          watch_date: watchData.watch_date,
          verified: watchData.verified,
          episode_watch_id: watchData.id,
        })
      }
      showSuccessToast("Episode marked as watched successfully")
    },
    onError: (error) => {
      const status = (error as any)?.status ?? (error as any)?.response?.status
      if (status === 409) {
        const detail =
          (error as any)?.body?.detail ??
          "Episode already has an unverified watch."
        showWarningToast(detail)
      } else {
        handleError.call(showErrorToast, error as any)
      }
    },
  })

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
      patchCaches(episode.id, { verified: true })
    },
    onSuccess: () => showSuccessToast("Episode verified successfully"),
    onError: (error) => handleError.call(showErrorToast, error as any),
  })

  const deleteWatchMutation = useMutation({
    mutationFn: () =>
      WatchesService.deleteWatch({ watchId: episode.episode_watch_id! }),
    onMutate: async () => {
      patchCaches(episode.id, {
        watch_date: null,
        verified: null,
        episode_watch_id: null,
      })
    },
    onSuccess: () => showSuccessToast("Watch deleted successfully"),
    onError: (error) => handleError.call(showErrorToast, error as any),
  })

  const onCardClick = () => {
    if (playlistId) markWatchedMutation.mutate(episode.id)
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
        verifyMutation.mutate()
      },
    })
  } else {
    menuItems.push({
      key: "watched",
      icon: <Check />,
      label: "Mark as Watched",
      disabled: !playlistId,
      onClick: (event) => {
        event.stopPropagation()
        if (playlistId) markWatchedMutation.mutate(episode.id)
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
  if (onHide) {
    menuItems.push({
      key: "hide",
      icon: <EyeOff />,
      label: "Temporarily Hide",
      onClick: (event) => {
        event.stopPropagation()
        onHide(episode.id)
      },
    })
  }
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
      <EpisodeCard
        episode={episode}
        menuItems={menuItems}
        topLeftBadge={topLeftBadge}
        onClick={onCardClick}
        editOrder={editOrder}
        index={index}
        onMove={onMove}
        onDrop={onDrop}
      />
      {confirmDeleteWatch && (
        <ConfirmDialog
          open={confirmDeleteWatch}
          onOpenChange={setConfirmDeleteWatch}
          title="Delete Last Watch"
          description={`Are you sure you want to delete the last watch for "${episode.name ?? ""}"? This will mark the episode as unwatched.`}
          confirmLabel="Delete"
          onConfirm={() => deleteWatchMutation.mutate()}
        />
      )}
    </>
  )
}
