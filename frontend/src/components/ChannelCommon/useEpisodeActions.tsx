// TODO: Validate
import { useMutation, useQueryClient } from "@tanstack/react-query"
import {
  BadgeCheck,
  Check,
  ExternalLink,
  EyeOff,
  Info,
  ListVideo,
  SkipForward,
  Trash2,
  Tv,
} from "lucide-react"
import { useState } from "react"
import { type ChannelEpisodesOutput, WatchesService } from "@/client"
import { BlacklistEpisodeDialog } from "@/components/Channels/ChannelDetail/BlacklistEpisodeDialog"
import type { EpisodeWithDetails } from "@/components/Channels/ChannelDetail/columns"
import { ConfirmDialog } from "@/components/Common/ConfirmDialog"
import type { ActionMenuItem } from "@/components/Common/ResponsiveActionMenu"
import useAuth from "@/hooks/useAuth"
import useCustomToast from "@/hooks/useCustomToast"
import { useMarkWatched } from "@/hooks/useMarkEpisodeWatched"
import { useOpenMedia } from "@/hooks/useOpenMedia"
import { isHiddenByWatchFilters, type WatchFilters } from "@/lib/watchFilters"
import { handleError } from "@/utils"

interface UseEpisodeActionsOptions {
  episode: EpisodeWithDetails
  channelId: string
  nextEpisodeId?: string | undefined
  onNextEpisode?: (currentEpisodeId: string) => void
  watchFilters?: WatchFilters
}

// TODO: Validate
/**
 * Build the shared episode action menu (mark watched, next, blacklist, …) and
 * the dialogs those actions open. Used by both the episode cards and the hero
 * billboard so the two offer the same actions.
 */
export function useEpisodeActions({
  episode,
  channelId,
  nextEpisodeId,
  onNextEpisode,
  watchFilters,
}: UseEpisodeActionsOptions) {
  const [confirmBlacklist, setConfirmBlacklist] = useState(false)
  const [confirmDeleteWatch, setConfirmDeleteWatch] = useState(false)
  const openMedia = useOpenMedia()
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const watchedMutation = useMarkWatched(channelId, watchFilters)

  const queryClient = useQueryClient()
  const completeMutation = useMutation({
    mutationFn: () =>
      WatchesService.updateWatch({
        watchId: episode.episode_watch_id!,
        requestBody: {
          watch_date: episode.watch_date!,
          completed: true,
        },
      }),
    onMutate: async () => {
      await queryClient.cancelQueries({ queryKey: ["episodes", channelId] })
      const previousEntries = queryClient.getQueriesData({
        queryKey: ["episodes", channelId],
      })
      // TODO: Validate
      const markCompleted = (oldData: ChannelEpisodesOutput | undefined) => {
        if (!oldData) return oldData
        // Completing leaves the episode watched, so it only drops out when
        // that is the state the filters hide.
        if (isHiddenByWatchFilters("watched", watchFilters)) {
          return {
            ...oldData,
            episodes: oldData.episodes.filter((ep) => ep.id !== episode.id),
          }
        }
        return {
          ...oldData,
          episodes: oldData.episodes.map((ep) =>
            ep.id === episode.id ? { ...ep, completed: true } : ep,
          ),
        }
      }
      queryClient.setQueriesData<ChannelEpisodesOutput>(
        { queryKey: ["episodes", channelId] },
        markCompleted,
      )
      queryClient.setQueriesData<ChannelEpisodesOutput>(
        { queryKey: ["episodes-preview", channelId] },
        markCompleted,
      )
      return { previousEntries }
    },
    onSuccess: () => {
      showSuccessToast("Episode completed successfully")
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
      // TODO: Validate
      const clearWatch = (
        oldData: ChannelEpisodesOutput | undefined,
      ): ChannelEpisodesOutput | undefined => {
        if (!oldData) return oldData
        // Deleting the watch leaves the episode unwatched, so it only drops out
        // when that is the state the filters hide.
        if (isHiddenByWatchFilters("unwatched", watchFilters)) {
          return {
            ...oldData,
            episodes: oldData.episodes.filter((ep) => ep.id !== episode.id),
          }
        }
        return {
          ...oldData,
          episodes: oldData.episodes.map((ep) =>
            ep.id === episode.id
              ? {
                  ...ep,
                  watch_date: null,
                  completed: null,
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

  const { user } = useAuth()

  const menuItems: ActionMenuItem[] = []
  if (episode.watch_date && !episode.completed && episode.episode_watch_id) {
    menuItems.push({
      key: "complete",
      icon: <BadgeCheck />,
      label: "Complete Watch",
      onClick: (event) => {
        event.stopPropagation()
        completeMutation.mutate(undefined)
      },
    })
  } else if (user) {
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
  if (user) {
    menuItems.push({
      key: "blacklist",
      icon: <EyeOff />,
      label: "Blacklist Episode",
      onClick: (event) => {
        event.stopPropagation()
        setConfirmBlacklist(true)
      },
    })
  }
  menuItems.push({
    key: "source-information",
    icon: episode.source.favicon_url ? (
      <img
        referrerPolicy="no-referrer"
        src={episode.source.favicon_url}
        alt=""
        className="size-4"
      />
    ) : (
      <Info />
    ),
    label: `${episode.source.key} Episode Information`,
    onClick: (event) => {
      event.stopPropagation()
      openMedia({ kind: "episode", episode: { id: episode.id } })
    },
  })
  if (episode.tmdb_episode_id && episode.tmdb_episode_id !== episode.id) {
    menuItems.push({
      key: "tmdb-information",
      icon: <img src="/tmdb.svg" alt="" className="size-4" />,
      label: "TMDB Episode Information",
      onClick: (event) => {
        event.stopPropagation()
        if (episode.tmdb_episode_id) {
          openMedia({
            kind: "episode",
            episode: { id: episode.tmdb_episode_id },
          })
        }
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
  const seasonUrl = episode.season.url
  if (seasonUrl) {
    menuItems.push({
      key: "open-season-url",
      icon: <ListVideo />,
      label: "Open Season Page",
      onClick: (event) => {
        event.stopPropagation()
        window.open(seasonUrl, "_blank", "noopener,noreferrer")
      },
    })
  }
  const titleUrl = episode.title.url
  if (titleUrl) {
    menuItems.push({
      key: "open-title-url",
      icon: <Tv />,
      label: "Open Title Page",
      onClick: (event) => {
        event.stopPropagation()
        window.open(titleUrl, "_blank", "noopener,noreferrer")
      },
    })
  }

  const dialogs = (
    <>
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

  return { menuItems, dialogs, watchedMutation }
}
