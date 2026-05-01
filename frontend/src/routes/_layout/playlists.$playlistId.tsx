// TODO: Validate
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { createFileRoute } from "@tanstack/react-router"
import { Globe, Lock, Save } from "lucide-react"
import { useEffect, useRef, useState } from "react"

import {
  EpisodesService,
  type PlaylistEpisodesOutput,
  PlaylistsService,
  type Visibility,
} from "@/client"
import { EditOrderButton } from "@/components/PlaylistChannelCommon/EditOrderButton"
import type {
  BaseEpisodeWithDetails,
  MoveDirection,
} from "@/components/PlaylistChannelCommon/EpisodeCard"
import {
  EPISODE_GRID_CLASSES,
  resolveArrowMove,
  useColumnCount,
} from "@/components/PlaylistChannelCommon/episodeGrid"
import { HeroBillboard } from "@/components/PlaylistChannelCommon/HeroBillboard"
import { PlaylistEpisodeCard } from "@/components/Playlists/PlaylistDetail/PlaylistEpisodeCard"
import DeletePlaylist from "@/components/Playlists/PlaylistList/DeletePlaylist"
import EditPlaylist from "@/components/Playlists/PlaylistList/EditPlaylist"
import { Button } from "@/components/ui/button"
import useAuth from "@/hooks/useAuth"
import useCustomToast from "@/hooks/useCustomToast"
import { usePersistedState } from "@/hooks/usePersistedState"

export const Route = createFileRoute("/_layout/playlists/$playlistId")({
  component: PlaylistDetail,
})

type PlaylistEpisodeWithDetails = BaseEpisodeWithDetails & { position: number }

function buildEpisodes(
  data: PlaylistEpisodesOutput,
): PlaylistEpisodeWithDetails[] {
  return data.episodes.map((episode) => {
    const season = data.seasons[episode.season_id]
    const show = data.shows[season.show_id]
    const source = data.sources[show.source_id]
    const plugin = data.plugins[source.plugin_id]
    return { ...episode, season, show, source, plugin }
  })
}

function PlaylistDetail() {
  const { playlistId } = Route.useParams()
  const { user } = useAuth()
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const gridRef = useRef<HTMLDivElement>(null)
  const columnCount = useColumnCount(gridRef)
  const [heroIndex, setHeroIndex] = useState(0)

  const { data: playlist, isLoading: isLoadingPlaylist } = useQuery({
    queryKey: ["playlist", playlistId],
    queryFn: () => PlaylistsService.getPlaylist({ playlistId }),
    refetchOnWindowFocus: false,
  })

  const { data: episodesData, isLoading: isLoadingEpisodes } = useQuery({
    queryKey: ["playlist-episodes", playlistId],
    queryFn: () => PlaylistsService.getPlaylistEpisodes({ playlistId }),
    refetchOnWindowFocus: false,
  })

  const serverEpisodes = episodesData ? buildEpisodes(episodesData) : []
  const isOwner = !!playlist && !!user && user.id === playlist.user_id

  const [editOrderFlag, setEditOrderFlag] = usePersistedState<"on" | "off">(
    `playlist-detail-edit-order:${playlistId}`,
    "off",
  )
  const editOrder = isOwner && editOrderFlag === "on"
  const setEditOrder = (next: boolean) => setEditOrderFlag(next ? "on" : "off")

  const [draftEpisodes, setDraftEpisodes] = useState<
    PlaylistEpisodeWithDetails[] | null
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
      PlaylistsService.updatePlaylist({
        playlistId,
        requestBody: {
          episode_ids: episodes.map((episode) => episode.id),
        },
      }),
    onSuccess: () => {
      showSuccessToast("Order saved")
      queryClient.invalidateQueries({
        queryKey: ["playlist-episodes", playlistId],
      })
      queryClient.invalidateQueries({
        queryKey: ["playlist-episodes-preview", playlistId],
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
      PlaylistsService.updatePlaylist({
        playlistId,
        requestBody: { visibility: next },
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["playlist", playlistId] })
      queryClient.invalidateQueries({ queryKey: ["playlists"] })
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
      EpisodesService.createWatch({
        episodeId,
        requestBody: {
          watch_date: new Date().toISOString(),
          verified: false,
        },
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["playlist-episodes", playlistId],
      })
      queryClient.invalidateQueries({
        queryKey: ["playlist-episodes-preview", playlistId],
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

  if (isLoadingPlaylist) {
    return (
      <div className="px-[4%] pt-4">
        <p className="text-sm text-muted-foreground">Loading playlist…</p>
      </div>
    )
  }

  if (!playlist) {
    return (
      <div className="px-[4%] pt-4">
        <p className="text-sm text-muted-foreground">Playlist not found.</p>
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
            {playlist.name ?? "(untitled)"}
          </h1>
          {isOwner && <EditPlaylist playlist={playlist} />}
          {isOwner && (
            <Button
              variant="outline"
              size="sm"
              onClick={() =>
                cycleVisibilityMutation.mutate(
                  nextVisibility(playlist.visibility ?? "private"),
                )
              }
              disabled={cycleVisibilityMutation.isPending}
              className="mt-2 mb-4"
            >
              {playlist.visibility === "public" && (
                <>
                  <Globe className="mr-1 size-4" /> Public
                </>
              )}
              {playlist.visibility === "unlisted" && (
                <>
                  <Globe className="mr-1 size-4" /> Unlisted
                </>
              )}
              {playlist.visibility === "private" && (
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
              className="mt-2 mb-4"
            >
              <Save />
              {saveOrderMutation.isPending ? "Saving…" : "Save Order"}
            </Button>
          )}
          {isOwner && <DeletePlaylist id={playlistId} />}
        </div>
        <p className="text-xs text-muted-foreground">
          {episodes.length} episode{episodes.length === 1 ? "" : "s"} · saved{" "}
          {new Date(playlist.created_at).toLocaleDateString()}
        </p>

        {isLoadingEpisodes ? (
          <p className="text-sm text-muted-foreground">Loading episodes…</p>
        ) : episodes.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            This playlist has no episodes.
          </p>
        ) : (
          <div ref={gridRef} className={EPISODE_GRID_CLASSES}>
            {episodes.map((episode, index) => (
              <PlaylistEpisodeCard
                key={episode.id}
                episode={episode}
                playlistId={playlistId}
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
