// TODO: Validate
import { useQueries, useQuery } from "@tanstack/react-query"
import { Link } from "@tanstack/react-router"
import { ChevronLeft, ChevronRight, Globe, Lock, Pencil } from "lucide-react"
import { useRef, useState } from "react"

import {
  type SnapshotAdminOutput,
  type SnapshotEpisodesOutput,
  type SnapshotPublicOutput,
  SnapshotsService,
} from "@/client"
import type { BaseEpisodeWithDetails } from "@/components/SnapshotChannelCommon/EpisodeCard"
import { SnapshotEpisodeCard } from "@/components/Snapshots/SnapshotDetail/SnapshotEpisodeCard"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import useAuth from "@/hooks/useAuth"
import DeleteSnapshot from "./DeleteSnapshot"
import EditSnapshot from "./EditSnapshot"

// Owner snapshots (full SnapshotAdminOutput) render edit controls; public snapshots
// (SnapshotPublicOutput) are read-only and only need the display fields both share.
type BrowseSnapshot = SnapshotAdminOutput | SnapshotPublicOutput

function buildEpisodes(data: SnapshotEpisodesOutput): BaseEpisodeWithDetails[] {
  return data.episodes.map((episode) => {
    const season = data.seasons[episode.season_id]
    const show = data.shows[season.show_id]
    const source = data.sources[show.source_id]
    const plugin = data.plugins[source.plugin_id]
    return { ...episode, season, show, source, plugin }
  })
}

function AdminEditSnapshot({ snapshot }: { snapshot: SnapshotPublicOutput }) {
  const [open, setOpen] = useState(false)
  const { data: fullSnapshot } = useQuery({
    queryKey: ["snapshot", snapshot.id, "admin-edit"],
    queryFn: () => SnapshotsService.getSnapshot({ snapshotId: snapshot.id }),
    enabled: open,
  })

  return (
    <>
      <Button
        variant="ghost"
        size="icon"
        title="Edit Snapshot"
        onClick={() => setOpen(true)}
      >
        <Pencil className="size-4" />
      </Button>
      {open && fullSnapshot && (
        <EditSnapshot
          snapshot={{ ...fullSnapshot, username: snapshot.username }}
          open={open}
          onOpenChange={setOpen}
          hideTrigger
        />
      )}
    </>
  )
}

interface SnapshotRowProps {
  snapshot: BrowseSnapshot
  readOnly?: boolean
  showCreatedBy?: boolean
}

function SnapshotRow({
  snapshot,
  readOnly = false,
  showCreatedBy = true,
}: SnapshotRowProps) {
  const scrollRef = useRef<HTMLDivElement>(null)
  const [showLeftArrow, setShowLeftArrow] = useState(false)
  const [showRightArrow, setShowRightArrow] = useState(true)
  const { user } = useAuth()
  const isAdmin = user?.is_superuser ?? false

  const { data, isLoading } = useQueries({
    queries: [
      {
        queryKey: ["snapshot-episodes-preview", snapshot.id],
        queryFn: () =>
          SnapshotsService.getSnapshotEpisodes({ snapshotId: snapshot.id }),
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
          to="/snapshots/$snapshotId"
          params={{ snapshotId: snapshot.id }}
          className="text-2xl font-bold hover:text-primary transition-colors"
        >
          {snapshot.name ?? "(untitled)"}
        </Link>
        {!readOnly && snapshot.visibility === "public" && (
          <Globe className="size-4 text-muted-foreground" aria-label="Public" />
        )}
        {!readOnly && snapshot.visibility === "unlisted" && (
          <Globe
            className="size-4 text-muted-foreground"
            aria-label="Unlisted"
          />
        )}
        {!readOnly && snapshot.visibility === "private" && (
          <Lock className="size-4 text-muted-foreground" aria-label="Private" />
        )}
        <div className="flex">
          {readOnly ? (
            isAdmin && (
              <AdminEditSnapshot snapshot={snapshot as SnapshotPublicOutput} />
            )
          ) : (
            <>
              {/* Reachable only when !readOnly, where snapshot is the owner's SnapshotAdminOutput. */}
              <EditSnapshot snapshot={snapshot as SnapshotAdminOutput} />
              <DeleteSnapshot id={snapshot.id} />
            </>
          )}
        </div>
      </div>

      {readOnly && showCreatedBy && (
        <p className="px-[4%] mb-2 text-sm text-muted-foreground">
          Created by{" "}
          {snapshot.user_id ? (
            <Link
              to="/users/$userId/snapshots"
              params={{ userId: snapshot.user_id }}
              className="underline hover:text-foreground"
            >
              {(snapshot as SnapshotPublicOutput).username || "Unnamed User"}
            </Link>
          ) : (
            "Anonymous"
          )}
        </p>
      )}

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
                  key={`skeleton-${snapshot.id}-${index}`}
                  className="shrink-0 w-70 md:w-85 lg:w-100 aspect-video rounded-sm"
                />
              ))
            : episodes.map((episode) => (
                <div
                  key={episode.id}
                  className="shrink-0 w-70 md:w-85 lg:w-100"
                >
                  <SnapshotEpisodeCard episode={episode} />
                </div>
              ))}

          {!isLoading && episodes.length === 0 && (
            <p className="text-sm text-muted-foreground py-8">
              No episodes in this snapshot
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

interface SnapshotsBrowseProps {
  snapshots: BrowseSnapshot[]
  readOnly?: boolean
  showCreatedBy?: boolean
}

export function SnapshotsBrowse({
  snapshots,
  readOnly = false,
  showCreatedBy = true,
}: SnapshotsBrowseProps) {
  // Public (read-only) lists arrive already ordered by the server (score then id),
  // so preserve that order. Owner lists are sorted by name locally.
  const sorted = readOnly
    ? snapshots
    : [...snapshots].sort((a, b) => (a.name ?? "").localeCompare(b.name ?? ""))

  return (
    <div className="flex flex-col gap-8 pb-8">
      {sorted.map((snapshot) => (
        <SnapshotRow
          key={snapshot.id}
          snapshot={snapshot}
          readOnly={readOnly}
          showCreatedBy={showCreatedBy}
        />
      ))}
      {snapshots.length === 0 && (
        <p className="text-center text-muted-foreground py-12">
          No snapshots yet. Open a channel and use "Save as Snapshot" to
          snapshot the current order.
        </p>
      )}
    </div>
  )
}
