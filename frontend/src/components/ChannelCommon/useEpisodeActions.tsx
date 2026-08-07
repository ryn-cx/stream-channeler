// TODO: Validate
import { useMutation, useQueryClient } from "@tanstack/react-query"
import {
  BadgeCheck,
  Check,
  ExternalLink,
  EyeOff,
  Flag,
  Info,
  SkipForward,
  Trash2,
} from "lucide-react"
import { useState } from "react"
import { type ChannelEpisodesOutput, WatchesService } from "@/client"
import { EpisodeInformationDialog } from "@/components/ChannelCommon/EpisodeInformationDialog"
import { ReportEpisodeIssueDialog } from "@/components/ChannelCommon/ReportEpisodeIssueDialog"
import { BlacklistEpisodeDialog } from "@/components/Channels/ChannelDetail/BlacklistEpisodeDialog"
import type { EpisodeWithDetails } from "@/components/Channels/ChannelDetail/columns"
import { ConfirmDialog } from "@/components/Common/ConfirmDialog"
import type { ActionMenuItem } from "@/components/Common/ResponsiveActionMenu"
import useCustomToast from "@/hooks/useCustomToast"
import { useMarkWatched } from "@/hooks/useMarkEpisodeWatched"
import { isHiddenByWatchFilters, type WatchFilters } from "@/lib/watchFilters"
import { handleError } from "@/utils"

interface UseEpisodeActionsOptions {
  episode: EpisodeWithDetails
  channelId: string
  nextEpisodeId?: string | undefined
  onNextEpisode?: (currentEpisodeId: string) => void
  watchFilters?: WatchFilters
}

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
  const [showInformation, setShowInformation] = useState(false)
  const [reportIssue, setReportIssue] = useState(false)
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const watchedMutation = useMarkWatched(channelId, watchFilters)

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
          // Verifying leaves the episode watched, so it only drops out when
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
    key: "information",
    icon: <Info />,
    label: "Episode Information",
    onClick: (event) => {
      event.stopPropagation()
      setShowInformation(true)
    },
  })
  menuItems.push({
    key: "report-issue",
    icon: <Flag />,
    label: episode.issue_report ? "Edit Issue Report" : "Report Issue",
    onClick: (event) => {
      event.stopPropagation()
      setReportIssue(true)
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

  const dialogs = (
    <>
      {showInformation && (
        <EpisodeInformationDialog
          episodeId={episode.id}
          open={showInformation}
          onOpenChange={setShowInformation}
        />
      )}
      {reportIssue && (
        <ReportEpisodeIssueDialog
          episodeId={episode.id}
          episodeName={episode.name ?? null}
          currentReport={episode.issue_report ?? null}
          open={reportIssue}
          onOpenChange={setReportIssue}
        />
      )}
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
