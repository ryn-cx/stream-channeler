// TODO: Validate
import { Loader2 } from "lucide-react"
import { useEffect, useRef, useState } from "react"
import { CaseViewer } from "./CaseViewer"
import type { StoreTitle } from "./caseTexture"
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
export function StoreScreen({
  storeKey,
  storeName,
  fetchStock,
  emptyMessage,
  back,
}: {
  storeKey: string
  storeName: string
  fetchStock: () => Promise<StoreStock>
  emptyMessage: string
  back: React.ReactNode
}) {
  const [stock, setStock] = useState<StoreStock | null>(null)
  const [filters, setFilters] = useState<StoreFilters | null>(null)
  const [filtersOpen, setFiltersOpen] = useState(false)
  const [store, setStore] = useState<VideoStore | null>(null)
  const [inspecting, setInspecting] = useState<StoreTitle | null>(null)
  const fetchRef = useRef(fetchStock)

  fetchRef.current = fetchStock

  // biome-ignore lint/correctness/useExhaustiveDependencies: restock from scratch whenever the store changes
  useEffect(() => {
    let cancelled = false
    setStock(null)

    // TODO: Validate
    const stockShelves = async () => {
      const shelved = await fetchRef.current()
      if (cancelled) return
      setStock(shelved)
      setFilters(defaultFilters(shelved))
    }

    stockShelves()
    return () => {
      cancelled = true
    }
  }, [storeKey])

  useEffect(() => {
    if (!store || !stock || !filters) return
    store.setFilterSummary(filterSummary(stock, filters))
  }, [store, stock, filters])

  // TODO: Validate
  const onActivate = (title: StoreTitle) => {
    setInspecting(title)
  }

  const shelved = stock && filters ? applyFilters(stock, filters) : []
  const slotCount = shelved.reduce(
    (total, title) => total + Math.max(title.genres.length, 1),
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
          paused={inspecting !== null || filtersOpen}
          onStore={setStore}
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
              <span className="text-sm">Unlocking the store…</span>
            </>
          )}
        </div>
      )}

      {stock && filters && (
        <StoreFilterPanel
          titles={stock}
          filters={filters}
          open={filtersOpen}
          onOpenChange={setFiltersOpen}
          onApply={setFilters}
        />
      )}

      {inspecting && (
        <CaseViewer title={inspecting} onClose={() => setInspecting(null)} />
      )}

      {back}
    </div>
  )
}
