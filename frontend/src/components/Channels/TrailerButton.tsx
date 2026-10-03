// TODO: Validate
import { useQuery } from "@tanstack/react-query"
import { Clapperboard, X } from "lucide-react"
import { useEffect, useState } from "react"
import { createPortal } from "react-dom"
import type { VideoStoreTrailerOutput } from "@/client"
import { fetchTitleDetail } from "@/components/Channels/Channel3D/titleDetail"
import { TrailerPlayer } from "@/components/Channels/TrailerPlayer"
import { Button } from "@/components/ui/button"

// TODO: Validate
function TrailerModal({
  trailers,
  isLoading,
  name,
  onClose,
}: {
  trailers: VideoStoreTrailerOutput[]
  isLoading: boolean
  name: string
  onClose: () => void
}) {
  useEffect(() => {
    // TODO: Validate
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose()
    }
    window.addEventListener("keydown", closeOnEscape)
    return () => window.removeEventListener("keydown", closeOnEscape)
  }, [onClose])

  return createPortal(
    <div
      role="dialog"
      aria-modal="true"
      aria-label={`${name} trailer`}
      className="fixed inset-0 z-[60] flex items-center justify-center bg-black"
    >
      <button
        type="button"
        onClick={onClose}
        className="absolute top-4 right-4 z-10 flex items-center gap-2 rounded-full bg-black/60 px-4 py-2 text-sm text-white/80 hover:text-white"
      >
        <X className="size-4" />
        Close
      </button>
      {trailers.length > 0 ? (
        <TrailerPlayer
          trailers={trailers}
          autoplay
          className="flex size-full flex-col gap-2 pb-3"
          frameClassName="min-h-0 w-full flex-1"
        />
      ) : (
        <p className="text-sm text-white/70">
          {isLoading ? "Loading trailer" : "No trailer available."}
        </p>
      )}
    </div>,
    document.body,
  )
}

// TODO: Validate
function FetchedTrailerModal({
  titleId,
  name,
  onClose,
}: {
  titleId: string
  name: string
  onClose: () => void
}) {
  const { data, isLoading } = useQuery({
    queryKey: ["video-store-title-detail", titleId, "tmdb"],
    queryFn: () => fetchTitleDetail(titleId, "tmdb"),
    refetchOnWindowFocus: false,
  })

  return (
    <TrailerModal
      trailers={data?.trailers ?? []}
      isLoading={isLoading}
      name={name}
      onClose={onClose}
    />
  )
}

// TODO: Validate
export function TrailerButton({
  titleId,
  name,
}: {
  titleId: string
  name: string
}) {
  const [open, setOpen] = useState(false)

  return (
    <>
      <Button variant="ghost" size="sm" onClick={() => setOpen(true)}>
        <Clapperboard />
        Trailer
      </Button>
      {open && (
        <FetchedTrailerModal
          titleId={titleId}
          name={name}
          onClose={() => setOpen(false)}
        />
      )}
    </>
  )
}
