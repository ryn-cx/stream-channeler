// TODO: Validate
import { Loader2 } from "lucide-react"
import { useEffect, useRef, useState } from "react"
import { CaseViewer } from "./CaseViewer"
import type { StoreTitle } from "./caseTexture"
import { VideoStoreCanvas } from "./VideoStoreCanvas"

export type StorePage = { titles: StoreTitle[]; total: number }

// TODO: Validate
export function StoreScreen({
  storeKey,
  storeName,
  pageSize,
  fetchPage,
  emptyMessage,
  back,
}: {
  storeKey: string
  storeName: string
  pageSize: number
  fetchPage: (offset: number) => Promise<StorePage>
  emptyMessage: string
  back: React.ReactNode
}) {
  const [stock, setStock] = useState<{
    capacity: number
    slotCount: number
    titles: StoreTitle[]
  } | null>(null)
  const [inspecting, setInspecting] = useState<StoreTitle | null>(null)
  const fetchRef = useRef(fetchPage)

  fetchRef.current = fetchPage

  // biome-ignore lint/correctness/useExhaustiveDependencies: restock from scratch whenever the store changes
  useEffect(() => {
    let cancelled = false
    const shelved = new Map<string, StoreTitle>()
    setStock(null)

    // TODO: Validate
    const shelve = (page: StorePage, slotCount: number) => {
      for (const title of page.titles) {
        if (!shelved.has(title.id)) shelved.set(title.id, title)
      }
      setStock({
        capacity: page.total,
        slotCount,
        titles: [...shelved.values()],
      })
    }

    // TODO: Validate
    const stockShelves = async () => {
      const first = await fetchRef.current(0)
      if (cancelled) return
      const placements = first.titles.reduce(
        (sum, title) => sum + Math.max(title.genres.length, 1),
        0,
      )
      const slotCount = Math.ceil(
        (first.total * placements * 1.2) / Math.max(first.titles.length, 1),
      )
      shelve(first, slotCount)

      const offsets: number[] = []
      for (let offset = pageSize; offset < first.total; offset += pageSize) {
        offsets.push(offset)
      }
      while (offsets.length > 0 && !cancelled) {
        const batch = offsets.splice(0, 4)
        const pages = await Promise.all(
          batch.map((offset) => fetchRef.current(offset)),
        )
        if (cancelled) return
        for (const page of pages) shelve(page, slotCount)
      }
    }

    stockShelves()
    return () => {
      cancelled = true
    }
  }, [storeKey, pageSize])

  // TODO: Validate
  const onActivate = (title: StoreTitle) => {
    setInspecting(title)
  }

  return (
    <div className="fixed inset-0 z-50 bg-black">
      {stock && stock.titles.length > 0 ? (
        <VideoStoreCanvas
          titles={stock.titles}
          capacity={stock.capacity}
          slotCount={stock.slotCount}
          storeName={storeName}
          paused={inspecting !== null}
          onActivate={onActivate}
        />
      ) : (
        <div className="flex size-full flex-col items-center justify-center gap-3 px-6 text-center text-white/70">
          {stock ? (
            <span>{emptyMessage}</span>
          ) : (
            <>
              <Loader2 className="size-6 animate-spin" />
              <span className="text-sm">Unlocking the store…</span>
            </>
          )}
        </div>
      )}

      {inspecting && (
        <CaseViewer title={inspecting} onClose={() => setInspecting(null)} />
      )}

      {back}
    </div>
  )
}
