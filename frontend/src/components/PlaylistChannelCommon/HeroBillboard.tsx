// TODO: Validate
import { ChevronLeft, ExternalLink, Play, SkipForward } from "lucide-react"

import type { BaseEpisodeWithDetails } from "@/components/PlaylistChannelCommon/EpisodeCard"
import { formatDuration } from "@/components/PlaylistChannelCommon/formatters"
import { Button } from "@/components/ui/button"

interface HeroBillboardProps {
  episode: BaseEpisodeWithDetails
  /** Called when the user clicks Play. Parents typically mark the episode
   * watched, open the URL, and advance to the next hero. */
  onPlay: () => void
  onSkip: () => void
  onBack: () => void
  hasNext: boolean
  hasPrev: boolean
}

export function HeroBillboard({
  episode,
  onPlay,
  onSkip,
  onBack,
  hasNext,
  hasPrev,
}: HeroBillboardProps) {
  const imageUrl =
    episode.image_url ||
    episode.season.image_url ||
    episode.show.image_url ||
    ""

  return (
    <div className="relative w-full md:aspect-video md:max-h-[65vh]">
      {imageUrl && (
        <img
          src={imageUrl}
          alt=""
          className="absolute inset-0 w-full h-full object-cover"
        />
      )}

      {/* Gradient overlays - always dark so text is readable in both themes */}
      <div className="absolute inset-0 bg-gradient-to-r from-black/80 via-black/40 to-transparent" />
      <div className="absolute inset-0 bg-gradient-to-t from-black/70 via-transparent to-black/20" />

      <div className="relative h-full flex flex-col">
        <div className="hidden md:block flex-1" />
        <div className="p-4 md:p-12 lg:p-16 flex flex-col gap-3 md:gap-4 max-w-full md:max-w-[66%]">
          <div className="flex flex-col gap-2">
            <p className="text-sm md:text-lg font-medium text-zinc-300 line-clamp-1">
              {episode.show.name}
              {episode.season.name ? ` - ${episode.season.name}` : ""}
            </p>
            <h2 className="text-2xl md:text-5xl lg:text-6xl font-bold text-white leading-tight line-clamp-2">
              {episode.name || `Episode ${episode.episode_number || ""}`}
            </h2>
          </div>

          <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm md:text-base text-zinc-300">
            {episode.duration != null && episode.duration > 0 && (
              <span>{formatDuration(episode.duration)}</span>
            )}
            {episode.air_date && (
              <span>{new Date(episode.air_date).toLocaleDateString()}</span>
            )}
            {episode.source.name && <span>{episode.source.name}</span>}
          </div>

          <div className="flex flex-wrap items-center gap-2 md:gap-3 mt-1 md:mt-2">
            {hasPrev && (
              <Button
                size="default"
                variant="secondary"
                className="bg-zinc-500/50 hover:bg-zinc-500/70 text-white gap-2 md:h-10 md:px-4"
                onClick={onBack}
              >
                <ChevronLeft className="size-5" />
                Back
              </Button>
            )}
            <Button
              size="default"
              className="bg-white text-black hover:bg-white/80 font-semibold gap-2 md:h-10 md:px-4"
              onClick={onPlay}
            >
              <Play className="size-5 fill-current" />
              Play
            </Button>
            {episode.url && (
              <Button
                size="default"
                variant="secondary"
                className="bg-zinc-500/50 hover:bg-zinc-500/70 text-white gap-2 md:h-10 md:px-4"
                onClick={() =>
                  window.open(episode.url!, "_blank", "noopener,noreferrer")
                }
              >
                <ExternalLink className="size-5" />
                Open
              </Button>
            )}
            {hasNext && (
              <Button
                size="default"
                variant="secondary"
                className="bg-zinc-500/50 hover:bg-zinc-500/70 text-white gap-2 md:h-10 md:px-4"
                onClick={onSkip}
              >
                <SkipForward className="size-5" />
                Next
              </Button>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
