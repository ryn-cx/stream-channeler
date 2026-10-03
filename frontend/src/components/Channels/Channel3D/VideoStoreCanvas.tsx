// TODO: Validate
import { useEffect, useRef, useState } from "react"
import { type StoreTitle, titleFacts } from "./caseTexture"
import { StoreLoading } from "./StoreLoading"
import { TouchControls } from "./TouchControls"
import { isTouchDevice, type StoreProgress, VideoStore } from "./videoStore"

// TODO: Validate
const shelfCapacity = (slotCount: number) =>
  Math.max(500, Math.ceil(slotCount / 500) * 500)

// TODO: Validate
const capacityKey = (storeKey: string) => `video-store-capacity:${storeKey}`

// TODO: Validate
const readCapacity = (storeKey: string) => {
  const stored = localStorage.getItem(capacityKey(storeKey))
  return stored ? Number(stored) : null
}

// TODO: Validate
const writeCapacity = (storeKey: string, capacity: number) => {
  localStorage.setItem(capacityKey(storeKey), String(capacity))
}

// TODO: Validate
export function VideoStoreCanvas({
  storeKey,
  stocked,
  titles,
  slotCount,
  genres,
  restockKey,
  storeName,
  metadata,
  paused,
  onStore,
  onFilters,
  onActivate,
  onChannelAction,
}: {
  storeKey: string
  stocked: boolean
  titles: StoreTitle[]
  slotCount: number
  genres: string[] | null
  restockKey: string
  storeName: string
  metadata: "tmdb" | "source"
  paused: boolean
  onStore?: (store: VideoStore | null) => void
  onFilters: () => void
  onActivate: (title: StoreTitle) => void
  onChannelAction: (action: "create" | "add") => void
}) {
  const containerRef = useRef<HTMLDivElement>(null)
  const activateRef = useRef(onActivate)
  const filtersRef = useRef(onFilters)
  const channelRef = useRef(onChannelAction)
  const storeRef = useRef(onStore)
  const nameRef = useRef(storeName)
  const [store, setStore] = useState<VideoStore | null>(null)
  const [focused, setFocused] = useState<StoreTitle | null>(null)
  const [locked, setLocked] = useState(false)
  const [progress, setProgress] = useState<StoreProgress>({
    stage: "building",
  })
  const [covers, setCovers] = useState(0)
  const [touch] = useState(isTouchDevice)
  const [capacity, setCapacity] = useState(
    () => readCapacity(storeKey) ?? shelfCapacity(slotCount),
  )
  const restockedRef = useRef<string | null>(null)

  activateRef.current = onActivate
  filtersRef.current = onFilters
  channelRef.current = onChannelAction
  storeRef.current = onStore
  nameRef.current = storeName
  const ready = progress.stage === "ready"

  useEffect(() => {
    if (!stocked) return
    setCapacity(shelfCapacity(slotCount))
  }, [slotCount, stocked])

  useEffect(() => {
    if (stocked) writeCapacity(storeKey, capacity)
  }, [storeKey, capacity, stocked])

  useEffect(() => {
    const container = containerRef.current
    if (!container) return
    const created = new VideoStore(
      container,
      capacity,
      nameRef.current,
      metadata,
      {
        onFocus: setFocused,
        onActivate: (title) => activateRef.current(title),
        onFilters: () => filtersRef.current(),
        onChannelAction: (action) => channelRef.current(action),
        onLockChange: setLocked,
        onProgress: setProgress,
        onCovers: setCovers,
      },
    )
    setStore(created)
    storeRef.current?.(created)
    return () => {
      setStore(null)
      setProgress({ stage: "building" })
      setCovers(0)
      storeRef.current?.(null)
      created.dispose()
    }
  }, [capacity, metadata])

  useEffect(() => {
    store?.setStoreName(storeName)
  }, [store, storeName])

  useEffect(() => {
    if (!store) return
    store.setShelfGenres(genres)
    if (restockedRef.current !== restockKey) {
      restockedRef.current = restockKey
      store.restock(titles)
      return
    }
    store.addTitles(titles)
  }, [titles, store, genres, restockKey])

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

      {!locked && !paused && ready && stocked && (
        <button
          type="button"
          onClick={() => {
            if (!paused) store?.lock()
          }}
          aria-label="Step back into the store"
          className="absolute inset-0 cursor-pointer"
        />
      )}

      {ready && stocked && covers > 0 && !paused && (
        <div className="pointer-events-none absolute left-4 top-16 rounded-full bg-black/60 px-4 py-2 text-xs text-white/70 backdrop-blur">
          {`Loading covers · ${covers.toLocaleString()} queued`}
        </div>
      )}

      {!(ready && stocked) && (
        <StoreLoading
          storeName={storeName}
          titleCount={stocked ? titles.length : null}
          progress={progress}
        />
      )}
    </div>
  )
}
