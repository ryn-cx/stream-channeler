// TODO: Validate
import { Loader2 } from "lucide-react"
import { useEffect, useRef, useState } from "react"
import { isLoggedIn } from "@/hooks/useAuth"
import { CaseViewer } from "./CaseViewer"
import { CounterChannels } from "./CounterChannels"
import { type StoreTitle, shelfGenres } from "./caseTexture"
import { defaultDesign, designSummary, type StoreDesign } from "./StoreDesign"
import {
  applyFilters,
  defaultFilters,
  filterSummary,
  StoreFilterPanel,
  type StoreFilters,
} from "./StoreFilters"
import { VideoStoreCanvas } from "./VideoStoreCanvas"
import type { VideoStore } from "./videoStore"

export type StoreStock = StoreTitle[]

// TODO: Validate
const counterKey = (storeKey: string) => `video-store-counter:${storeKey}`

// TODO: Validate
const readCounter = (storeKey: string): StoreTitle[] => {
  const stored = localStorage.getItem(counterKey(storeKey))
  return stored ? JSON.parse(stored) : []
}

// TODO: Validate
const writeCounter = (storeKey: string, titles: StoreTitle[]) => {
  localStorage.setItem(counterKey(storeKey), JSON.stringify(titles))
}

// TODO: Validate
const designKeyFor = (storeKey: string) => `video-store-design:${storeKey}`

// TODO: Validate
const readDefaultDesign = (): Partial<StoreDesign> | null => {
  const stored = localStorage.getItem("video-store-design-default")
  return stored ? JSON.parse(stored) : null
}

// TODO: Validate
const writeDefaultDesign = (design: StoreDesign) => {
  localStorage.setItem("video-store-design-default", JSON.stringify(design))
}

// TODO: Validate
const readDesign = (storeKey: string): Partial<StoreDesign> => {
  const stored = localStorage.getItem(designKeyFor(storeKey))
  return stored ? JSON.parse(stored) : (readDefaultDesign() ?? {})
}

// TODO: Validate
const writeDesign = (storeKey: string, design: StoreDesign) => {
  localStorage.setItem(designKeyFor(storeKey), JSON.stringify(design))
}

// TODO: Validate
const filterKeyFor = (storeKey: string) => `video-store-filters:${storeKey}`

// TODO: Validate
const readDefaultFilters = (): Partial<StoreFilters> | null => {
  const stored = localStorage.getItem("video-store-filters-default")
  return stored ? JSON.parse(stored) : null
}

// TODO: Validate
const writeDefaultFilters = (filters: StoreFilters) => {
  localStorage.setItem("video-store-filters-default", JSON.stringify(filters))
}

// TODO: Validate
const readFilters = (storeKey: string): Partial<StoreFilters> => {
  const stored = localStorage.getItem(filterKeyFor(storeKey))
  return stored ? JSON.parse(stored) : (readDefaultFilters() ?? {})
}

// TODO: Validate
const writeFilters = (storeKey: string, filters: StoreFilters) => {
  localStorage.setItem(filterKeyFor(storeKey), JSON.stringify(filters))
}

// TODO: Validate
export function StoreScreen({
  storeKey,
  storeName,
  fetchStock,
  emptyMessage,
  back,
  metadata = "tmdb",
  onMetadata,
}: {
  storeKey: string
  storeName: string
  fetchStock: () => Promise<StoreStock>
  emptyMessage: string
  back: React.ReactNode
  metadata?: "tmdb" | "source"
  onMetadata?: (metadata: "tmdb" | "source") => void
}) {
  const [stock, setStock] = useState<StoreStock | null>(null)
  const [filters, setFilters] = useState<StoreFilters | null>(null)
  const [filtersOpen, setFiltersOpen] = useState(false)
  const [store, setStore] = useState<VideoStore | null>(null)
  const [design, setDesign] = useState<StoreDesign>(defaultDesign)
  const [hasDesignDefault, setHasDesignDefault] = useState(
    readDefaultDesign() !== null,
  )
  const [hasFilterDefault, setHasFilterDefault] = useState(
    readDefaultFilters() !== null,
  )
  const [inspecting, setInspecting] = useState<StoreTitle | null>(null)
  const [vhs, setVhs] = useState(false)
  const [counter, setCounter] = useState<StoreTitle[]>([])
  const [flash, setFlash] = useState<string | null>(null)
  const [audioPlaying, setAudioPlaying] = useState(false)
  const [channelAction, setChannelAction] = useState<"create" | "add" | null>(
    null,
  )
  const fetchRef = useRef(fetchStock)
  const stockedKey = useRef<string | null>(null)

  fetchRef.current = fetchStock

  useEffect(() => {
    let cancelled = false
    if (stockedKey.current !== storeKey) {
      stockedKey.current = storeKey
      setStock(null)
    }

    // TODO: Validate
    const stockShelves = async () => {
      const shelved = await fetchRef.current()
      if (cancelled) return
      setStock(shelved)
      setFilters({
        ...defaultFilters(shelved),
        ...readFilters(storeKey),
      })
    }

    stockShelves()
    return () => {
      cancelled = true
    }
  }, [storeKey])

  useEffect(() => {
    if (!store || !stock || !filters) return
    store.setBoard(filterSummary(stock, filters), designSummary(design))
  }, [store, stock, filters, design])

  useEffect(() => {
    const restored = { ...defaultDesign, ...readDesign(storeKey) }
    setCounter(readCounter(storeKey))
    setDesign(restored)
    setAudioPlaying(restored.audioAutoplay)
  }, [storeKey])

  useEffect(() => {
    if (!flash) return
    const handle = setTimeout(() => setFlash(null), 2600)
    return () => clearTimeout(handle)
  }, [flash])

  useEffect(() => {
    store?.setCounter(counter)
  }, [store, counter])

  useEffect(() => {
    store?.setChannelButtons(isLoggedIn())
  }, [store])

  useEffect(() => {
    if (!store) return
    store.setFloorColor(design.floor)
    store.setRoomColor(design.room)
    store.setReflections(design.shine)
    store.setUnlit(design.unlit)
    store.setFormat(design.format)
    store.setLights(design.lights)
    store.setOutdoorLights(design.outdoor)
    store.setAskew(design.askew)
    store.setRain(design.rainDrops, design.rainSpeed)
  }, [store, design])

  // TODO: Validate
  const onActivate = (title: StoreTitle) => {
    setVhs(store?.isVhs() ?? false)
    setInspecting(title)
  }

  const shelved = stock && filters ? applyFilters(stock, filters) : []
  const slotCount = shelved.reduce(
    (total, title) => total + Math.max(shelfGenres(title).length, 1),
    0,
  )
  const filterKey = filters ? JSON.stringify(filters) : ""

  return (
    <div className="fixed inset-0 z-50 bg-black">
      {shelved.length > 0 ? (
        <VideoStoreCanvas
          key={filterKey}
          titles={shelved}
          slotCount={slotCount}
          storeName={storeName}
          metadata={metadata}
          paused={inspecting !== null || filtersOpen || channelAction !== null}
          onStore={setStore}
          onFilters={() => setFiltersOpen(true)}
          onChannelAction={setChannelAction}
          onActivate={onActivate}
        />
      ) : (
        <div className="flex size-full flex-col items-center justify-center gap-3 px-6 text-center text-white/70">
          {stock ? (
            <span>
              {stock.length > 0
                ? "Nothing matches these filters."
                : emptyMessage}
            </span>
          ) : (
            <>
              <Loader2 className="size-6 animate-spin" />
              <span className="text-sm">Loading…</span>
            </>
          )}
        </div>
      )}

      {stock && filters && (
        <StoreFilterPanel
          titles={stock}
          filters={filters}
          design={design}
          onDesign={(next) => {
            writeDesign(storeKey, next)
            setDesign(next)
          }}
          open={filtersOpen}
          onOpenChange={setFiltersOpen}
          onApply={(next) => {
            writeFilters(storeKey, next)
            setFilters(next)
          }}
          hasDesignDefault={hasDesignDefault}
          hasFilterDefault={hasFilterDefault}
          onSaveDesignDefault={(next) => {
            writeDefaultDesign(next)
            setHasDesignDefault(true)
          }}
          onSaveFilterDefault={(next) => {
            writeDefaultFilters(next)
            setHasFilterDefault(true)
          }}
          onLoadDesignDefault={() => {
            const stored = readDefaultDesign()
            if (!stored) return
            const next = { ...defaultDesign, ...stored }
            writeDesign(storeKey, next)
            setDesign(next)
          }}
          onLoadFilterDefault={() => {
            const stored = readDefaultFilters()
            if (!stored || !stock) return
            const next = { ...defaultFilters(stock), ...stored }
            writeFilters(storeKey, next)
            setFilters(next)
          }}
          audioPlaying={audioPlaying}
          onAudioPlaying={setAudioPlaying}
          metadata={metadata}
          onMetadata={onMetadata}
        />
      )}

      {flash && (
        <div className="pointer-events-none absolute inset-x-0 top-6 z-40 flex justify-center">
          <div className="max-w-[90vw] truncate rounded-full border border-emerald-300/40 bg-black/80 px-5 py-2 text-sm text-emerald-100 backdrop-blur">
            {flash}
          </div>
        </div>
      )}

      {channelAction && (
        <CounterChannels
          action={channelAction}
          titles={counter}
          onClose={() => setChannelAction(null)}
        />
      )}

      {inspecting && (
        <CaseViewer
          title={inspecting}
          vhs={vhs}
          metadata={metadata}
          onClose={() => setInspecting(null)}
          atCounter={counter.some((entry) => entry.id === inspecting.id)}
          onTakeToCounter={() => {
            const next = [
              ...counter.filter((entry) => entry.id !== inspecting.id),
              inspecting,
            ]
            writeCounter(storeKey, next)
            setCounter(next)
            setFlash(
              `${inspecting.name} is waiting at the counter · ${next.length} held`,
            )
            setInspecting(null)
          }}
          onRemoveFromCounter={() => {
            const next = counter.filter((entry) => entry.id !== inspecting.id)
            writeCounter(storeKey, next)
            setCounter(next)
            setFlash(`${inspecting.name} went back on the shelf`)
            setInspecting(null)
          }}
        />
      )}

      {back}
    </div>
  )
}
