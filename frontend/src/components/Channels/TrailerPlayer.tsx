// TODO: Validate
import { ChevronLeft, ChevronRight } from "lucide-react"
import { useState } from "react"
import type { VideoStoreTrailerOutput } from "@/client"

// TODO: Validate
export const embedUrl = (url: string, autoplay: boolean) => {
  const parsed = new URL(url)
  const autoplayFlag = autoplay ? 1 : 0
  if (parsed.hostname.endsWith("vimeo.com")) {
    return `https://player.vimeo.com/video/${parsed.pathname.slice(1)}?autoplay=${autoplayFlag}`
  }
  return `https://www.youtube.com/embed/${parsed.searchParams.get("v")}?autoplay=${autoplayFlag}&rel=0`
}

// TODO: Validate
export function TrailerPlayer({
  trailers,
  autoplay,
  className,
  frameClassName,
}: {
  trailers: VideoStoreTrailerOutput[]
  autoplay: boolean
  className: string
  frameClassName: string
}) {
  const [trailerIndex, setTrailerIndex] = useState(0)

  return (
    <div className={className}>
      <iframe
        key={trailers[trailerIndex].url}
        src={embedUrl(trailers[trailerIndex].url, autoplay)}
        title={trailers[trailerIndex].name ?? "Trailer"}
        allow="autoplay; encrypted-media; picture-in-picture; fullscreen"
        allowFullScreen
        referrerPolicy="strict-origin-when-cross-origin"
        className={frameClassName}
      />
      <div className="flex items-center gap-2 text-sm text-white/80">
        {trailers.length > 1 && (
          <button
            type="button"
            onClick={() =>
              setTrailerIndex(
                (trailerIndex - 1 + trailers.length) % trailers.length,
              )
            }
            className="rounded-full bg-black/60 p-2 hover:text-white"
            aria-label="Previous trailer"
          >
            <ChevronLeft className="size-4" />
          </button>
        )}
        <span className="flex min-w-0 flex-1 items-center justify-center gap-2">
          <span className="shrink-0 rounded-full border border-white/25 px-2 py-0.5 text-xs font-medium text-white">
            {trailers[trailerIndex].type}
          </span>
          <span className="truncate">
            {trailers[trailerIndex].name ?? "Trailer"}
            {trailers.length > 1 &&
              ` (${trailerIndex + 1} of ${trailers.length})`}
          </span>
        </span>
        {trailers.length > 1 && (
          <button
            type="button"
            onClick={() =>
              setTrailerIndex((trailerIndex + 1) % trailers.length)
            }
            className="rounded-full bg-black/60 p-2 hover:text-white"
            aria-label="Next trailer"
          >
            <ChevronRight className="size-4" />
          </button>
        )}
      </div>
    </div>
  )
}
