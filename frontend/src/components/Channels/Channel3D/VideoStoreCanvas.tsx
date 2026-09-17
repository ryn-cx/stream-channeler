// TODO: Validate
import { useEffect, useRef, useState } from "react"
import { type StoreTitle, titleFacts } from "./caseTexture"
import { TouchControls } from "./TouchControls"
import { isTouchDevice, VideoStore } from "./videoStore"

// TODO: Validate
export function VideoStoreCanvas({
  titles,
  slotCount,
  storeName,
  paused,
  onStore,
  onFilters,
  onActivate,
}: {
  titles: StoreTitle[]
  slotCount: number
  storeName: string
  paused: boolean
  onStore?: (store: VideoStore | null) => void
  onFilters: () => void
  onActivate: (title: StoreTitle) => void
}) {
  const containerRef = useRef<HTMLDivElement>(null)
  const activateRef = useRef(onActivate)
  const filtersRef = useRef(onFilters)
  const storeRef = useRef(onStore)
  const [store, setStore] = useState<VideoStore | null>(null)
  const [focused, setFocused] = useState<StoreTitle | null>(null)
  const [locked, setLocked] = useState(false)
  const [entered, setEntered] = useState(false)
  const [touch] = useState(isTouchDevice)

  activateRef.current = onActivate
  filtersRef.current = onFilters
  storeRef.current = onStore

  useEffect(() => {
    const container = containerRef.current
    if (!container) return
    const created = new VideoStore(container, slotCount, storeName, {
      onFocus: setFocused,
      onActivate: (title) => activateRef.current(title),
      onFilters: () => filtersRef.current(),
      onLockChange: (value) => {
        setLocked(value)
        if (value) setEntered(true)
      },
    })
    setStore(created)
    storeRef.current?.(created)
    return () => {
      setStore(null)
      storeRef.current?.(null)
      created.dispose()
    }
  }, [slotCount, storeName])

  useEffect(() => {
    store?.addTitles(titles)
  }, [titles, store])

  return (
    <div className="absolute inset-0 overflow-hidden bg-black">
      <div ref={containerRef} className="size-full touch-none" />

      {locked && (
        <>
          <div className="pointer-events-none absolute inset-0">
            {!touch && (
              <div className="absolute left-1/2 top-1/2 size-1.5 -translate-x-1/2 -translate-y-1/2 rounded-full bg-white/70 shadow-[0_0_6px_rgba(0,0,0,0.9)]" />
            )}

            {focused && (
              <div
                className={`absolute left-1/2 w-[min(28rem,80vw)] -translate-x-1/2 rounded-lg border border-white/15 bg-black/70 px-4 py-3 text-center backdrop-blur ${touch ? "top-16" : "bottom-24"}`}
              >
                <div className="truncate text-lg font-semibold text-white">
                  {focused.name}
                </div>
                <div className="mt-0.5 text-xs text-white/60">
                  {[focused.year, ...titleFacts(focused)]
                    .filter(Boolean)
                    .join(" · ")}
                </div>
              </div>
            )}

            {!touch && (
              <div className="absolute bottom-5 left-1/2 -translate-x-1/2 rounded-full bg-black/55 px-4 py-1.5 text-[11px] text-white/55 backdrop-blur">
                WASD move · Mouse look · Shift run · C crouch · Click to inspect
                · Esc exit
              </div>
            )}
          </div>

          {touch && !paused && <TouchControls store={store} />}
        </>
      )}

      {!locked && entered && !paused && (
        <button
          type="button"
          onClick={() => {
            if (!paused) store?.lock()
          }}
          aria-label="Step back into the store"
          className="absolute inset-0 cursor-pointer"
        />
      )}

      {!locked && !entered && !paused && (
        <button
          type="button"
          onClick={() => store?.lock()}
          className="absolute inset-0 flex flex-col items-center justify-center gap-3 bg-black/70 px-6 text-white backdrop-blur-sm"
        >
          <span className="text-3xl font-bold tracking-tight">{storeName}</span>
          <span className="text-sm text-white/60">
            {`${titles.length} ${titles.length === 1 ? "title" : "titles"} on the shelves`}
          </span>
          <span className="mt-3 rounded-full border border-white/25 px-5 py-2 text-sm font-medium">
            {touch ? "Tap to walk in" : "Click to walk in"}
          </span>
          <span className="text-center text-[11px] text-white/40">
            {touch
              ? "Left side to move, right side to look, tap a case to pick it up"
              : "WASD to move, mouse to look, C to crouch, click a case to inspect it, Esc to step out"}
          </span>
        </button>
      )}
    </div>
  )
}
