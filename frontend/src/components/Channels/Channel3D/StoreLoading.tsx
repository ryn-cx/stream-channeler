// TODO: Validate
import { Check, Loader2 } from "lucide-react"
import { useEffect, useState } from "react"
import type { StoreProgress } from "./videoStore"

// TODO: Validate
const storeStep = (progress: StoreProgress) => {
  if (progress.stage === "building") return "Building the store…"
  if (progress.stage === "starting") return "Starting the renderer…"
  return "Store built"
}

// TODO: Validate
const shaderStep = (progress: StoreProgress) => {
  if (progress.stage !== "compiling") return "Shaders compiled"
  if (progress.total === 0) return "Compiling shaders…"
  return `Compiling shaders · ${progress.compiled} / ${progress.total}`
}

// TODO: Validate
function LoadingStep({ done, label }: { done: boolean; label: string }) {
  return (
    <div className="flex items-center gap-2">
      {done ? (
        <Check className="size-4 text-emerald-300" />
      ) : (
        <Loader2 className="size-4 animate-spin text-white/60" />
      )}
      <span className={done ? "text-white/80" : "text-white/60"}>{label}</span>
    </div>
  )
}

// TODO: Validate
export function StoreLoading({
  storeName,
  titleCount,
  progress,
}: {
  storeName: string
  titleCount: number | null
  progress: StoreProgress
}) {
  const [startedAt] = useState(() => performance.now())
  const [elapsed, setElapsed] = useState(0)

  useEffect(() => {
    const handle = setInterval(
      () => setElapsed(Math.floor((performance.now() - startedAt) / 1000)),
      1000,
    )
    return () => clearInterval(handle)
  }, [startedAt])

  return (
    <div
      className={`absolute inset-0 flex flex-col items-center justify-center gap-4 px-6 text-center text-white ${progress.stage === "compiling" || progress.stage === "ready" ? "bg-black/60" : "bg-black"}`}
    >
      <span className="text-3xl font-bold tracking-tight">{storeName}</span>
      <div className="flex flex-col gap-1.5 rounded-lg bg-black/60 px-4 py-3 text-left text-sm backdrop-blur">
        <LoadingStep
          done={titleCount !== null}
          label={
            titleCount === null
              ? "Fetching the catalogue…"
              : `${titleCount.toLocaleString()} ${titleCount === 1 ? "title" : "titles"} in stock`
          }
        />
        <LoadingStep
          done={progress.stage === "compiling" || progress.stage === "ready"}
          label={storeStep(progress)}
        />
        {(progress.stage === "compiling" || progress.stage === "ready") && (
          <LoadingStep
            done={progress.stage === "ready"}
            label={shaderStep(progress)}
          />
        )}
      </div>
      <span className="text-[11px] text-white/40">{elapsed}s</span>
    </div>
  )
}
