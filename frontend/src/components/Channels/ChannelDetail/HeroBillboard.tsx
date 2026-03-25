// TODO: Validate
import { ChevronLeft, ExternalLink, Play, SkipForward } from "lucide-react"

import { Button } from "@/components/ui/button"
import { useMarkWatched } from "@/hooks/useMarkEpisodeWatched"
import type { EpisodeWithDetails } from "./columns"
import { formatDuration } from "./EpisodeCards"

interface HeroBillboardProps {
  episode: EpisodeWithDetails
  channelId: string
  onPlay: () => void
  onSkip: () => void
  onBack: () => void
  hasNext: boolean
  hasPrev: boolean
}

export function HeroBillboard({
  episode,
  channelId,
  onPlay,
  onSkip,
  onBack,
  hasNext,
  hasPrev,
}: HeroBillboardProps) {
  const watchedMutation = useMarkWatched(channelId)

  const imageUrl =
    episode.image_url ||
    episode.season.image_url ||
    episode.show.image_url ||
    ""

  const handlePlay = () => {
    watchedMutation.mutate(episode.id)
    if (episode.url) {
      window.open(episode.url, "_blank", "noopener,noreferrer")
    }
    onPlay()
  }

  return (
    <div className="relative w-full aspect-video">
      {/* Background image */}
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

      {/* Sticky content wrapper - spacer pushes content to bottom, sticky pulls it to viewport */}
      <div className="relative h-full flex flex-col">
        <div className="flex-1" />
        <div className="sticky bottom-0 p-6 md:p-12 lg:p-16 flex flex-col gap-4 max-w-[66%]">
          <div className="flex flex-col gap-2">
            <p className="text-base md:text-lg font-medium text-zinc-300">
              {episode.show.name}
              {episode.season.name ? ` - ${episode.season.name}` : ""}
            </p>
            <h2 className="text-3xl md:text-5xl lg:text-6xl font-bold text-white leading-tight">
              {episode.name || `Episode ${episode.episode_number || ""}`}
            </h2>
          </div>

          <div className="flex items-center gap-3 text-base text-zinc-300">
            {episode.duration != null && episode.duration > 0 && (
              <span>{formatDuration(episode.duration)}</span>
            )}
            {episode.air_date && (
              <span>{new Date(episode.air_date).toLocaleDateString()}</span>
            )}
            {episode.source.name && <span>{episode.source.name}</span>}
          </div>

          {episode.description && (
            <p className="text-sm text-zinc-300 line-clamp-3 whitespace-pre-line">
              {episode.description}
            </p>
          )}

          <div className="flex items-center gap-3 mt-2">
            {hasPrev && (
              <Button
                size="lg"
                variant="secondary"
                className="bg-zinc-500/50 hover:bg-zinc-500/70 text-white gap-2"
                onClick={onBack}
              >
                <ChevronLeft className="size-5" />
                Back
              </Button>
            )}
            <Button
              size="lg"
              className="bg-white text-black hover:bg-white/80 font-semibold gap-2"
              onClick={handlePlay}
            >
              <Play className="size-5 fill-current" />
              Play
            </Button>
            {episode.url && (
              <Button
                size="lg"
                variant="secondary"
                className="bg-zinc-500/50 hover:bg-zinc-500/70 text-white gap-2"
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
                size="lg"
                variant="secondary"
                className="bg-zinc-500/50 hover:bg-zinc-500/70 text-white gap-2"
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
