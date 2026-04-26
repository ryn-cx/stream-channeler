// TODO: Validate
import { useQueries } from "@tanstack/react-query"
import { Link } from "@tanstack/react-router"
import { ChevronLeft, ChevronRight, Globe, Lock } from "lucide-react"
import { useRef, useState } from "react"
import { createPortal } from "react-dom"

import {
  type PlaylistEpisodesOutput,
  type PlaylistOutput,
  PlaylistsService,
} from "@/client"
import type { BaseEpisodeWithDetails } from "@/components/PlaylistChannelCommon/EpisodeCard"
import { PlaylistEpisodeCard } from "@/components/Playlists/PlaylistDetail/PlaylistEpisodeCard"
import { Skeleton } from "@/components/ui/skeleton"
import DeletePlaylist from "./DeletePlaylist"
import EditPlaylist from "./EditPlaylist"

function buildEpisodes(data: PlaylistEpisodesOutput): BaseEpisodeWithDetails[] {
  return data.episodes.map((episode) => {
    const season = data.seasons[episode.season_id]
    const show = data.shows[season.show_id]
    const source = data.sources[show.source_id]
    const plugin = data.plugins[source.plugin_id]
    return { ...episode, season, show, source, plugin }
  })
}

interface PlaylistRowProps {
  playlist: PlaylistOutput
  onDelete: (playlist: PlaylistOutput) => void
}

function PlaylistRow({ playlist }: PlaylistRowProps) {
  const scrollRef = useRef<HTMLDivElement>(null)
  const [showLeftArrow, setShowLeftArrow] = useState(false)
  const [showRightArrow, setShowRightArrow] = useState(true)

  const { data, isLoading } = useQueries({
    queries: [
      {
        queryKey: ["playlist-episodes-preview", playlist.id],
        queryFn: () =>
          PlaylistsService.getPlaylistEpisodes({ playlistId: playlist.id }),
        refetchOnWindowFocus: false,
        refetchOnMount: false,
      },
    ],
  })[0]

  const updateArrows = () => {
    const container = scrollRef.current
    if (!container) return
    setShowLeftArrow(container.scrollLeft > 10)
    setShowRightArrow(
      container.scrollLeft < container.scrollWidth - container.clientWidth - 10,
    )
  }

  const scroll = (direction: "left" | "right") => {
    const container = scrollRef.current
    if (!container) return
    const scrollAmount = container.clientWidth * 0.8
    container.scrollBy({
      left: direction === "left" ? -scrollAmount : scrollAmount,
      behavior: "smooth",
    })
  }

  const episodes = data ? buildEpisodes(data) : []

  return (
    <div className="group/row relative">
      <div className="flex items-center gap-3 mb-2 px-[4%]">
        <Link
          to="/playlists/$playlistId"
          params={{ playlistId: playlist.id }}
          className="text-2xl font-bold hover:text-primary transition-colors"
        >
          {playlist.name ?? "(untitled)"}
        </Link>
        {playlist.public ? (
          <Globe className="size-4 text-muted-foreground" aria-label="Public" />
        ) : (
          <Lock className="size-4 text-muted-foreground" aria-label="Private" />
        )}
        <div className="flex">
          <EditPlaylist playlist={playlist} />
          <DeletePlaylist id={playlist.id} />
        </div>
      </div>

      <div className="relative">
        {showLeftArrow && (
          <button
            type="button"
            className="absolute left-0 top-0 bottom-0 z-20 h-full w-10 rounded-none bg-background/50 opacity-0 group-hover/row:opacity-100 transition-opacity flex items-center justify-center"
            onClick={() => scroll("left")}
            aria-label="Scroll left"
          >
            <ChevronLeft className="size-6" />
          </button>
        )}

        <div
          ref={scrollRef}
          className="flex gap-2 overflow-x-auto scrollbar-hide px-[4%] pb-2"
          onScroll={updateArrows}
        >
          {isLoading
            ? Array.from({ length: 8 }).map((_, index) => (
                <Skeleton
                  key={`skeleton-${playlist.id}-${index}`}
                  className="shrink-0 w-70 md:w-85 lg:w-100 aspect-video rounded-sm"
                />
              ))
            : episodes.map((episode) => (
                <div
                  key={episode.id}
                  className="shrink-0 w-70 md:w-85 lg:w-100"
                >
                  <PlaylistEpisodeCard episode={episode} />
                </div>
              ))}

          {!isLoading && episodes.length === 0 && (
            <p className="text-sm text-muted-foreground py-8">
              No episodes in this playlist
            </p>
          )}
        </div>

        {showRightArrow && episodes.length > 0 && (
          <button
            type="button"
            className="absolute right-0 top-0 bottom-0 z-20 h-full w-10 rounded-none bg-background/50 opacity-0 group-hover/row:opacity-100 transition-opacity flex items-center justify-center"
            onClick={() => scroll("right")}
            aria-label="Scroll right"
          >
            <ChevronRight className="size-6" />
          </button>
        )}
      </div>
    </div>
  )
}

interface PlaylistsBrowseProps {
  playlists: PlaylistOutput[]
}

export function PlaylistsBrowse({ playlists }: PlaylistsBrowseProps) {
  const sorted = [...playlists].sort((a, b) =>
    (a.name ?? "").localeCompare(b.name ?? ""),
  )
  const [deletePlaylist, setDeletePlaylist] = useState<PlaylistOutput | null>(
    null,
  )

  return (
    <div className="flex flex-col gap-8 pb-8">
      {sorted.map((playlist) => (
        <PlaylistRow
          key={playlist.id}
          playlist={playlist}
          onDelete={setDeletePlaylist}
        />
      ))}
      {playlists.length === 0 && (
        <p className="text-center text-muted-foreground py-12">
          No playlists yet. Open a channel and use "Save as Playlist" to
          snapshot the current order.
        </p>
      )}

      {deletePlaylist &&
        createPortal(
          <DeletePlaylist
            key={deletePlaylist.id}
            id={deletePlaylist.id}
            externalOpen
            onExternalClose={() => setDeletePlaylist(null)}
          />,
          document.body,
        )}
    </div>
  )
}
