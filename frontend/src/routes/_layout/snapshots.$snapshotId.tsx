// TODO: Validate
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { createFileRoute } from "@tanstack/react-router"
import { Globe, Lock, Save } from "lucide-react"
import { useEffect, useRef, useState } from "react"

import {
  type SnapshotEpisodesOutput,
  SnapshotsService,
  type Visibility,
  WatchesService,
} from "@/client"
import { EditOrderButton } from "@/components/SnapshotChannelCommon/EditOrderButton"
import type {
  BaseEpisodeWithDetails,
  MoveDirection,
} from "@/components/SnapshotChannelCommon/EpisodeCard"
import {
  EPISODE_GRID_CLASSES,
  resolveArrowMove,
  useColumnCount,
} from "@/components/SnapshotChannelCommon/episodeGrid"
import { HeroBillboard } from "@/components/SnapshotChannelCommon/HeroBillboard"
import { SnapshotEpisodeCard } from "@/components/Snapshots/SnapshotDetail/SnapshotEpisodeCard"
import DeleteSnapshot from "@/components/Snapshots/SnapshotList/DeleteSnapshot"
import EditSnapshot from "@/components/Snapshots/SnapshotList/EditSnapshot"
import { Button } from "@/components/ui/button"
import useAuth from "@/hooks/useAuth"
import useCustomToast from "@/hooks/useCustomToast"
import { usePersistedState } from "@/hooks/usePersistedState"

export const Route = createFileRoute("/_layout/snapshots/$snapshotId")({
  component: SnapshotDetail,
})

type SnapshotEpisodeWithDetails = BaseEpisodeWithDetails & { position: number }

function buildEpisodes(
  data: SnapshotEpisodesOutput,
): SnapshotEpisodeWithDetails[] {
  return data.episodes.map((episode) => {
    const season = data.seasons[episode.season_id]
    const show = data.shows[season.show_id]
    const source = data.sources[show.source_id]
    const plugin = data.plugins[source.plugin_id]
    return { ...episode, season, show, source, plugin }
  })
}

function SnapshotDetail() {
  const { snapshotId } = Route.useParams()
  const { user } = useAuth()
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const gridRef = useRef<HTMLDivElement>(null)
  const columnCount = useColumnCount(gridRef)
  const [heroIndex, setHeroIndex] = useState(0)

  const { data: snapshot, isLoading: isLoadingSnapshot } = useQuery({
    queryKey: ["snapshot", snapshotId],
    queryFn: () => SnapshotsService.getSnapshot({ snapshotId }),
    refetchOnWindowFocus: false,
  })

  const { data: episodesData, isLoading: isLoadingEpisodes } = useQuery({
    queryKey: ["snapshot-episodes", snapshotId],
    queryFn: () => SnapshotsService.getSnapshotEpisodes({ snapshotId }),
    refetchOnWindowFocus: false,
  })

  const serverEpisodes = episodesData ? buildEpisodes(episodesData) : []
  const isOwner = !!snapshot && !!user && user.id === snapshot.user_id

  const [editOrderFlag, setEditOrderFlag] = usePersistedState<"on" | "off">(
    `snapshot-detail-edit-order:${snapshotId}`,
    "off",
  )
  const editOrder = isOwner && editOrderFlag === "on"
  const setEditOrder = (next: boolean) => setEditOrderFlag(next ? "on" : "off")

  const [draftEpisodes, setDraftEpisodes] = useState<
    SnapshotEpisodeWithDetails[] | null
  >(null)

  // Reset the working draft whenever fresh server data arrives.
  useEffect(() => {
    if (episodesData) {
      setDraftEpisodes(buildEpisodes(episodesData))
    }
  }, [episodesData])

  const episodes = draftEpisodes ?? serverEpisodes

  const isDirty = (() => {
    if (!draftEpisodes || !episodesData) return false
    if (draftEpisodes.length !== serverEpisodes.length) return true
    for (let i = 0; i < draftEpisodes.length; i++) {
      if (draftEpisodes[i].id !== serverEpisodes[i].id) return true
    }
    return false
  })()

  const swapEpisodes = (fromIndex: number, toIndex: number) => {
    if (fromIndex === toIndex) return
    setDraftEpisodes((current) => {
      if (!current) return current
      if (
        fromIndex < 0 ||
        toIndex < 0 ||
        fromIndex >= current.length ||
        toIndex >= current.length
      ) {
        return current
      }
      const next = [...current]
      ;[next[fromIndex], next[toIndex]] = [next[toIndex], next[fromIndex]]
      return next
    })
  }

  const moveEpisode = (fromIndex: number, toIndex: number) => {
    if (fromIndex === toIndex) return
    setDraftEpisodes((current) => {
      if (!current) return current
      if (
        fromIndex < 0 ||
        toIndex < 0 ||
        fromIndex >= current.length ||
        toIndex >= current.length
      ) {
        return current
      }
      const next = [...current]
      const [moved] = next.splice(fromIndex, 1)
      next.splice(toIndex, 0, moved)
      return next
    })
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

  const handleHide = (episodeId: string) => {
    setDraftEpisodes((current) =>
      current ? current.filter((episode) => episode.id !== episodeId) : current,
    )
  }

  const saveOrderMutation = useMutation({
    mutationFn: () =>
      SnapshotsService.updateSnapshot({
        snapshotId,
        requestBody: {
          episode_ids: episodes.map((episode) => episode.id),
        },
      }),
    onSuccess: () => {
      showSuccessToast("Order saved")
      queryClient.invalidateQueries({
        queryKey: ["snapshot-episodes", snapshotId],
      })
      queryClient.invalidateQueries({
        queryKey: ["snapshot-episodes-preview", snapshotId],
      })
      setEditOrder(false)
    },
    onError: (error: unknown) => {
      const message = error instanceof Error ? error.message : String(error)
      showErrorToast(`Could not save order: ${message}`)
    },
  })

  const cycleVisibilityMutation = useMutation({
    mutationFn: (next: Visibility) =>
      SnapshotsService.updateSnapshot({
        snapshotId,
        requestBody: { visibility: next },
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["snapshot", snapshotId] })
      queryClient.invalidateQueries({ queryKey: ["snapshots"] })
    },
    onError: (error: unknown) => {
      const message = error instanceof Error ? error.message : String(error)
      showErrorToast(`Could not change visibility: ${message}`)
    },
  })

  const nextVisibility = (current: Visibility): Visibility => {
    if (current === "public") return "unlisted"
    if (current === "unlisted") return "private"
    return "public"
  }

  const playHeroMutation = useMutation({
    mutationFn: (episodeId: string) =>
      WatchesService.createWatch({
        episodeId,
        requestBody: {
          watch_date: new Date().toISOString(),
          verified: false,
        },
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["snapshot-episodes", snapshotId],
      })
      queryClient.invalidateQueries({
        queryKey: ["snapshot-episodes-preview", snapshotId],
      })
    },
    onError: (error: unknown) => {
      const status = (error as any)?.status ?? (error as any)?.response?.status
      // 409 means an unverified watch already exists — silently ignore here.
      if (status !== 409) {
        const message = error instanceof Error ? error.message : String(error)
        showErrorToast(`Could not mark watched: ${message}`)
      }
    },
  })

  if (isLoadingSnapshot) {
    return (
      <div className="px-[4%] pt-4">
        <p className="text-sm text-muted-foreground">Loading snapshot…</p>
      </div>
    )
  }

  if (!snapshot) {
    return (
      <div className="px-[4%] pt-4">
        <p className="text-sm text-muted-foreground">Snapshot not found.</p>
      </div>
    )
  }

  const heroEpisode = episodes[heroIndex] ?? episodes[0]
  const showHero = !editOrder && episodes.length > 0
  const hasNextHero = heroIndex < episodes.length - 1
  const hasPrevHero = heroIndex > 0

  return (
    <div className="flex flex-col">
      {showHero && heroEpisode && (
        <HeroBillboard
          episode={heroEpisode}
          onPlay={() => {
            playHeroMutation.mutate(heroEpisode.id)
            if (heroEpisode.url) {
              window.open(heroEpisode.url, "_blank", "noopener,noreferrer")
            }
            if (hasNextHero) setHeroIndex(heroIndex + 1)
          }}
          onSkip={() => {
            if (hasNextHero) setHeroIndex(heroIndex + 1)
          }}
          onBack={() => {
            if (hasPrevHero) setHeroIndex(heroIndex - 1)
          }}
          hasNext={hasNextHero}
          hasPrev={hasPrevHero}
        />
      )}

      <div className="px-[4%] pt-4 pb-8 space-y-4">
        <div className="flex flex-wrap items-center gap-2">
          <h1 className="text-2xl font-bold tracking-tight">
            {snapshot.name ?? "(untitled)"}
          </h1>
          {isOwner && <EditSnapshot snapshot={snapshot} />}
          {isOwner && (
            <Button
              variant="outline"
              size="sm"
              onClick={() =>
                cycleVisibilityMutation.mutate(
                  nextVisibility(snapshot.visibility ?? "private"),
                )
              }
              disabled={cycleVisibilityMutation.isPending}
              className="my-4"
            >
              {snapshot.visibility === "public" && (
                <>
                  <Globe className="mr-1 size-4" /> Public
                </>
              )}
              {snapshot.visibility === "unlisted" && (
                <>
                  <Globe className="mr-1 size-4" /> Unlisted
                </>
              )}
              {snapshot.visibility === "private" && (
                <>
                  <Lock className="mr-1 size-4" /> Private
                </>
              )}
            </Button>
          )}
          {isOwner && (
            <EditOrderButton
              editOrder={editOrder}
              onToggle={() => setEditOrder(!editOrder)}
            />
          )}
          {isOwner && (
            <Button
              onClick={() => saveOrderMutation.mutate()}
              disabled={!isDirty || saveOrderMutation.isPending}
              className="my-4"
            >
              <Save />
              {saveOrderMutation.isPending ? "Saving…" : "Save Order"}
            </Button>
          )}
          {isOwner && <DeleteSnapshot id={snapshotId} />}
        </div>
        <p className="text-xs text-muted-foreground">
          {episodes.length} episode{episodes.length === 1 ? "" : "s"} · saved{" "}
          {new Date(snapshot.created_at).toLocaleDateString()}
        </p>

        {isLoadingEpisodes ? (
          <p className="text-sm text-muted-foreground">Loading episodes…</p>
        ) : episodes.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            This snapshot has no episodes.
          </p>
        ) : (
          <div ref={gridRef} className={EPISODE_GRID_CLASSES}>
            {episodes.map((episode, index) => (
              <SnapshotEpisodeCard
                key={episode.id}
                episode={episode}
                snapshotId={snapshotId}
                onHide={handleHide}
                editOrder={editOrder}
                index={index}
                onMove={handleArrowMove}
                onDrop={moveEpisode}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
