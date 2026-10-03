// TODO: Validate
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { Check, Play } from "lucide-react"

import { WatchesService } from "@/client"
import { CollapsibleSection } from "@/components/ChannelCommon/CollapsibleSection"
import { LoadingButton } from "@/components/ui/loading-button"
import useAuth from "@/hooks/useAuth"
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"
import CompleteWatch from "./CompleteWatch"
import DeleteWatch from "./DeleteWatch"
import EditWatch from "./EditWatch"

interface EpisodeWatchHistoryProps {
  episodeId: string
  /** Whether the history is wanted yet, so a collapsed reading fetches nothing. */
  enabled: boolean
}

// TODO: Validate
/**
 * Every time the reader has watched this episode, and the making of another.
 *
 * A watch is held against the row that played it, so what is read here is every
 * watch of the episode itself rather than of the one row it was opened from.
 */
export function EpisodeWatchHistory({
  episodeId,
  enabled,
}: EpisodeWatchHistoryProps) {
  const { user } = useAuth()
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const queryClient = useQueryClient()

  const { data: watches, isLoading } = useQuery({
    queryKey: ["watches", "episode", episodeId],
    queryFn: () => WatchesService.getEpisodeWatches({ episodeId }),
    enabled: enabled && Boolean(user),
  })

  const createMutation = useMutation({
    mutationFn: (completed: boolean) =>
      WatchesService.createWatch({
        episodeId,
        requestBody: { watch_date: new Date().toISOString(), completed },
      }),
    onSuccess: () => {
      showSuccessToast("Watch recorded")
      queryClient.invalidateQueries({ queryKey: ["watches"] })
    },
    onError: (error: unknown) =>
      handleError.call(
        showErrorToast,
        error as Parameters<typeof handleError>[0],
      ),
  })

  const completeMutation = useMutation({
    mutationFn: (watchId: string) =>
      WatchesService.updateWatch({
        watchId,
        requestBody: { completed: true },
      }),
    onSuccess: () => {
      showSuccessToast("Watch completed")
      queryClient.invalidateQueries({ queryKey: ["watches"] })
    },
    onError: (error: unknown) =>
      handleError.call(
        showErrorToast,
        error as Parameters<typeof handleError>[0],
      ),
  })

  // A watch left open is the one a completion is of, since the episode was
  // already started and the server takes only one open watch at a time.
  const openWatch = watches?.find((watch) => !watch.completed)

  // A watch is held against the reader, so there is nothing to read and nothing
  // to record until there is a reader to hold it.
  if (!user) return null

  return (
    <CollapsibleSection title="Watch History" defaultOpen>
      <div className="flex flex-col gap-2">
        {isLoading ? (
          <p className="text-sm text-muted-foreground">Reading the watches…</p>
        ) : !watches || watches.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            You have not watched this episode yet.
          </p>
        ) : (
          <div className="rounded-md border">
            {watches.map((watch) => (
              <div
                key={watch.id}
                className="flex items-center gap-2 border-b px-3 py-2 text-sm last:border-b-0"
              >
                <span className="flex-1">
                  {new Date(watch.watch_date).toLocaleString()}
                  {watch.completed ? null : (
                    <span className="ml-2 text-xs text-muted-foreground">
                      Incomplete
                    </span>
                  )}
                </span>
                {watch.completed ? null : (
                  <CompleteWatch id={watch.id} completed={watch.completed} />
                )}
                <EditWatch watch={watch} />
                <DeleteWatch id={watch.id} />
              </div>
            ))}
          </div>
        )}
        <div className="flex flex-wrap gap-2">
          <LoadingButton
            variant="outline"
            size="sm"
            disabled={Boolean(openWatch)}
            loading={createMutation.isPending}
            onClick={() => createMutation.mutate(false)}
          >
            <Play className="h-4 w-4" />
            Started watching
          </LoadingButton>
          <LoadingButton
            variant="outline"
            size="sm"
            loading={completeMutation.isPending}
            onClick={() =>
              openWatch
                ? completeMutation.mutate(openWatch.id)
                : createMutation.mutate(true)
            }
          >
            <Check className="h-4 w-4" />
            Completed watching
          </LoadingButton>
        </div>
      </div>
    </CollapsibleSection>
  )
}
