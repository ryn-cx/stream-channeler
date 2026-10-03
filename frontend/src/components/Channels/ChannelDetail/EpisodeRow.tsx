// TODO: Validate
import { ChevronLeft, ChevronRight } from "lucide-react"
import { useRef, useState } from "react"

import { Button } from "@/components/ui/button"
import type { EpisodeWithDetails } from "./columns"
import { EpisodeTile } from "./EpisodeTile"

interface EpisodeRowProps {
  title: string
  episodes: EpisodeWithDetails[]
  channelId: string
  nextEpisodeMap: Map<string, string>
  onNextEpisode: (currentEpisodeId: string) => void
}

// TODO: Validate
export function EpisodeRow({
  title,
  episodes,
  channelId,
  nextEpisodeMap,
  onNextEpisode,
}: EpisodeRowProps) {
  const scrollRef = useRef<HTMLDivElement>(null)
  const [showLeftArrow, setShowLeftArrow] = useState(false)
  const [showRightArrow, setShowRightArrow] = useState(true)

  // TODO: Validate
  const updateArrows = () => {
    const container = scrollRef.current
    if (!container) return
    setShowLeftArrow(container.scrollLeft > 10)
    setShowRightArrow(
      container.scrollLeft < container.scrollWidth - container.clientWidth - 10,
    )
  }

  // TODO: Validate
  const scroll = (direction: "left" | "right") => {
    const container = scrollRef.current
    if (!container) return
    const scrollAmount = container.clientWidth * 0.8
    container.scrollBy({
      left: direction === "left" ? -scrollAmount : scrollAmount,
      behavior: "smooth",
    })
  }

  return (
    <div className="group/row relative">
      <h3 className="text-lg font-semibold mb-2 px-[4%]">{title}</h3>

      <div className="relative">
        {/* Left arrow */}
        {showLeftArrow && (
          <Button
            variant="ghost"
            size="icon"
            className="absolute left-0 top-0 bottom-0 z-20 h-full w-10 rounded-none bg-background/50 opacity-0 group-hover/row:opacity-100 transition-opacity"
            onClick={() => scroll("left")}
          >
            <ChevronLeft className="size-6" />
          </Button>
        )}

        {/* Scrollable container */}
        <div
          ref={scrollRef}
          className="flex gap-2 overflow-x-auto overflow-y-visible scrollbar-hide px-[4%] pb-4"
          onScroll={updateArrows}
        >
          {episodes.map((episode) => (
            <EpisodeTile
              key={episode.id}
              episode={episode}
              channelId={channelId}
              nextEpisodeId={nextEpisodeMap.get(episode.id)}
              onNextEpisode={onNextEpisode}
            />
          ))}
        </div>

        {/* Right arrow */}
        {showRightArrow && (
          <Button
            variant="ghost"
            size="icon"
            className="absolute right-0 top-0 bottom-0 z-20 h-full w-10 rounded-none bg-background/50 opacity-0 group-hover/row:opacity-100 transition-opacity"
            onClick={() => scroll("right")}
          >
            <ChevronRight className="size-6" />
          </Button>
        )}
      </div>
    </div>
  )
}
