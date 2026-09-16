// TODO: Validate
import { useEffect, useRef, useState } from "react"
import type { StoreTitle } from "./caseTexture"
import { VideoStore } from "./videoStore"

// TODO: Validate
export function VideoStoreCanvas({
  titles,
  channelName,
  onActivate,
}: {
  titles: StoreTitle[]
  channelName: string
  onActivate: (title: StoreTitle) => void
}) {
  const containerRef = useRef<HTMLDivElement>(null)
  const storeRef = useRef<VideoStore | null>(null)
  const activateRef = useRef(onActivate)
  const [focused, setFocused] = useState<StoreTitle | null>(null)
  const [locked, setLocked] = useState(false)

  activateRef.current = onActivate

  useEffect(() => {
    const container = containerRef.current
    if (!container) return
    const store = new VideoStore(container, titles, channelName, {
      onFocus: setFocused,
      onActivate: (title) => activateRef.current(title),
      onLockChange: setLocked,
    })
    storeRef.current = store
    return () => {
      storeRef.current = null
      store.dispose()
    }
  }, [titles, channelName])

  return (
    <div className="absolute inset-0 overflow-hidden bg-black">
      <div ref={containerRef} className="size-full" />

      {locked && (
        <div className="pointer-events-none absolute inset-0">
          <div className="absolute left-1/2 top-1/2 size-1.5 -translate-x-1/2 -translate-y-1/2 rounded-full bg-white/70 shadow-[0_0_6px_rgba(0,0,0,0.9)]" />

          {focused && (
            <div className="absolute bottom-24 left-1/2 w-[min(28rem,80vw)] -translate-x-1/2 rounded-lg border border-white/15 bg-black/70 px-4 py-3 text-center backdrop-blur">
              <div className="truncate text-lg font-semibold text-white">
                {focused.name}
              </div>
              <div className="mt-0.5 text-xs text-white/60">
                {focused.year && `${focused.year} · `}
                {focused.seasonCount > 0 &&
                  `${focused.seasonCount} ${focused.seasonCount === 1 ? "season" : "seasons"} · `}
                {focused.episodeCount}{" "}
                {focused.episodeCount === 1 ? "episode" : "episodes"}
              </div>
              {focused.url && (
                <div className="mt-2 text-xs font-medium tracking-wide text-emerald-300">
                  Press E to take it to the counter
                </div>
              )}
            </div>
          )}

          <div className="absolute bottom-5 left-1/2 -translate-x-1/2 rounded-full bg-black/55 px-4 py-1.5 text-[11px] text-white/55 backdrop-blur">
            WASD move · Mouse look · Shift run · C crouch · E open · Esc exit
          </div>
        </div>
      )}

      {!locked && (
        <button
          type="button"
          onClick={() => storeRef.current?.lock()}
          className="absolute inset-0 flex flex-col items-center justify-center gap-3 bg-black/70 text-white backdrop-blur-sm"
        >
          <span className="text-3xl font-bold tracking-tight">
            {channelName}
          </span>
          <span className="text-sm text-white/60">
            {titles.length} {titles.length === 1 ? "title" : "titles"} on the
            shelves
          </span>
          <span className="mt-3 rounded-full border border-white/25 px-5 py-2 text-sm font-medium">
            Click to walk in
          </span>
          <span className="text-[11px] text-white/40">
            WASD to move, mouse to look, C to crouch, E to grab a case, Esc to
            step out
          </span>
        </button>
      )}
    </div>
  )
}
