// TODO: Validate
import {
  ChevronDown,
  ChevronFirst,
  ChevronLast,
  ChevronLeft,
  ChevronRight,
  ChevronUp,
} from "lucide-react"
import { lazy, Suspense } from "react"

import type {
  EpisodeOutput,
  PluginOutput,
  SeasonOutput,
  ShowPublic,
  SourcePublic,
} from "@/client"
import {
  type ActionMenuItem,
  ResponsiveActionMenu,
} from "@/components/Common/ResponsiveActionMenu"
import { Card } from "@/components/ui/card"

/** Episode shape required by the shared card layout and overlays. */
export type BaseEpisodeWithDetails = EpisodeOutput & {
  season: SeasonOutput
  show: ShowPublic
  source: SourcePublic
  plugin: PluginOutput
}

export type MoveDirection = "up" | "down" | "left" | "right" | "first" | "last"

const allModules = import.meta.glob<{
  default: React.ComponentType<{ episode: BaseEpisodeWithDetails }>
}>("../Channels/ChannelDetail/CardOverlays/*/*.tsx", { eager: false })

const pluginFormats: Record<
  string,
  Record<
    string,
    React.LazyExoticComponent<
      React.ComponentType<{ episode: BaseEpisodeWithDetails }>
    >
  >
> = {}

const genericFormats: Record<
  string,
  React.LazyExoticComponent<
    React.ComponentType<{ episode: BaseEpisodeWithDetails }>
  >
> = {}

for (const path in allModules) {
  const match = path.match(/CardOverlays\/([^/]+)\/(.+?)\.tsx$/)
  if (match) {
    const pluginKey = match[1]
    const mediaType = match[2]
    const loader = allModules[path] as () => Promise<{
      default: React.ComponentType<{ episode: BaseEpisodeWithDetails }>
    }>
    if (pluginKey === "generic") {
      genericFormats[mediaType] = lazy(loader)
    } else {
      if (!pluginFormats[pluginKey]) pluginFormats[pluginKey] = {}
      pluginFormats[pluginKey][mediaType] = lazy(loader)
    }
  }
}

function EpisodeCardOverlay({ episode }: { episode: BaseEpisodeWithDetails }) {
  const mediaType = episode.show.media_type || ""
  const pluginKey = episode.plugin.key

  let OverlayComponent: React.LazyExoticComponent<
    React.ComponentType<{ episode: BaseEpisodeWithDetails }>
  > | null = null

  if (pluginFormats[pluginKey]) {
    OverlayComponent = pluginFormats[pluginKey][mediaType] || null
  }
  if (!OverlayComponent) {
    OverlayComponent = genericFormats[mediaType] || null
  }
  if (!OverlayComponent) {
    OverlayComponent = genericFormats.generic || null
  }

  return (
    <Suspense fallback={null}>
      {OverlayComponent && <OverlayComponent episode={episode} />}
    </Suspense>
  )
}

interface EpisodeCardProps {
  episode: BaseEpisodeWithDetails
  /** Actions shown in the top-right responsive menu. */
  menuItems: ActionMenuItem[]
  /** Optional content shown as a top-left overlay (e.g. "Last Watched"). */
  topLeftBadge?: React.ReactNode
  /** Click handler for the card itself. Ignored when in edit-order mode. */
  onClick?: () => void
  /** Fades the card out to show it has already been clicked. */
  dimmed?: boolean
  /** Whether the card is currently in reorder mode. */
  editOrder?: boolean
  /** Position in the list — required for reorder callbacks to work. */
  index?: number
  onMove?: (index: number, direction: MoveDirection) => void
  onDrop?: (fromIndex: number, toIndex: number) => void
}

export function EpisodeCard({
  episode,
  menuItems,
  topLeftBadge,
  onClick,
  dimmed,
  editOrder,
  index,
  onMove,
  onDrop,
}: EpisodeCardProps) {
  const imageUrl =
    episode.image_url ||
    episode.season.image_url ||
    episode.show.image_url ||
    ""

  const moveArrowBaseClass =
    "absolute z-20 h-7 w-7 rounded-full bg-background/90 hover:bg-background text-foreground shadow-md flex items-center justify-center transition-colors"

  const handleArrowClick = (
    event: React.MouseEvent<HTMLButtonElement>,
    direction: MoveDirection,
  ) => {
    event.preventDefault()
    event.stopPropagation()
    if (index !== undefined) onMove?.(index, direction)
  }

  return (
    <Card
      className={`group overflow-hidden cursor-pointer hover:bg-accent transition p-0 bg-card no-border rounded-lg ${
        dimmed ? "opacity-40" : ""
      } ${editOrder ? "ring-2 ring-green-600/60" : ""}`}
      onClick={() => {
        if (editOrder) return
        onClick?.()
      }}
      draggable={editOrder && index !== undefined}
      onDragStart={(event) => {
        if (!editOrder || index === undefined) return
        event.dataTransfer.effectAllowed = "move"
        event.dataTransfer.setData("text/plain", String(index))
      }}
      onDragOver={(event) => {
        if (!editOrder) return
        event.preventDefault()
        event.dataTransfer.dropEffect = "move"
      }}
      onDrop={(event) => {
        if (!editOrder || index === undefined) return
        event.preventDefault()
        const fromIndex = Number(event.dataTransfer.getData("text/plain"))
        if (Number.isFinite(fromIndex) && fromIndex !== index) {
          onDrop?.(fromIndex, index)
        }
      }}
    >
      <div className="relative shrink-0 aspect-video overflow-hidden">
        {editOrder && index !== undefined && (
          <>
            <button
              type="button"
              aria-label="Move to front"
              className={`${moveArrowBaseClass} top-1 left-1`}
              onClick={(event) => handleArrowClick(event, "first")}
            >
              <ChevronFirst className="h-4 w-4" />
            </button>
            <button
              type="button"
              aria-label="Move to end"
              className={`${moveArrowBaseClass} bottom-1 right-1`}
              onClick={(event) => handleArrowClick(event, "last")}
            >
              <ChevronLast className="h-4 w-4" />
            </button>
            <button
              type="button"
              aria-label="Move up"
              className={`${moveArrowBaseClass} top-1 left-1/2 -translate-x-1/2`}
              onClick={(event) => handleArrowClick(event, "up")}
            >
              <ChevronUp className="h-4 w-4" />
            </button>
            <button
              type="button"
              aria-label="Move down"
              className={`${moveArrowBaseClass} bottom-1 left-1/2 -translate-x-1/2`}
              onClick={(event) => handleArrowClick(event, "down")}
            >
              <ChevronDown className="h-4 w-4" />
            </button>
            <button
              type="button"
              aria-label="Move left"
              className={`${moveArrowBaseClass} left-1 top-1/2 -translate-y-1/2`}
              onClick={(event) => handleArrowClick(event, "left")}
            >
              <ChevronLeft className="h-4 w-4" />
            </button>
            <button
              type="button"
              aria-label="Move right"
              className={`${moveArrowBaseClass} right-1 top-1/2 -translate-y-1/2`}
              onClick={(event) => handleArrowClick(event, "right")}
            >
              <ChevronRight className="h-4 w-4" />
            </button>
          </>
        )}
        <img
          loading="lazy"
          src={imageUrl}
          alt={`Episode ${episode.episode_number} - ${episode.name ?? ""}`}
          className="w-full h-full object-cover transition-opacity group-hover:opacity-80"
        />

        {topLeftBadge ? (
          <div className="absolute top-0 left-0 z-10">{topLeftBadge}</div>
        ) : null}

        <div className="absolute top-2 right-2 z-10">
          <ResponsiveActionMenu
            items={menuItems}
            onTriggerClick={(event) => event.stopPropagation()}
          />
        </div>
      </div>

      <div className="px-2 pb-2">
        <EpisodeCardOverlay episode={episode} />
      </div>
    </Card>
  )
}
