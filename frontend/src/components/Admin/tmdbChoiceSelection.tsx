// TODO: Validate
import {
  createContext,
  type ReactNode,
  useCallback,
  useContext,
  useMemo,
  useState,
} from "react"

interface TmdbChoiceSelection {
  selectedFor: (episodeId: string) => string[]
  isSelected: (episodeId: string, tmdbEpisodeId: string) => boolean
  toggle: (episodeId: string, tmdbEpisodeId: string) => void
  clear: (episodeId: string) => void
}

const TmdbChoiceSelectionContext = createContext<TmdbChoiceSelection | null>(
  null,
)

// TODO: Validate
export function useTmdbChoiceSelection() {
  return useContext(TmdbChoiceSelectionContext)
}

// TODO: Validate
export function TmdbChoiceSelectionProvider({
  children,
}: {
  children: ReactNode
}) {
  const [selectedIds, setSelectedIds] = useState<Record<string, string[]>>({})

  const toggle = useCallback((episodeId: string, tmdbEpisodeId: string) => {
    setSelectedIds((previous) => {
      const current = previous[episodeId] ?? []
      return {
        ...previous,
        [episodeId]: current.includes(tmdbEpisodeId)
          ? current.filter((id) => id !== tmdbEpisodeId)
          : [...current, tmdbEpisodeId],
      }
    })
  }, [])

  const clear = useCallback((episodeId: string) => {
    setSelectedIds((previous) => {
      const remaining = { ...previous }
      delete remaining[episodeId]
      return remaining
    })
  }, [])

  const value = useMemo<TmdbChoiceSelection>(
    () => ({
      selectedFor: (episodeId) => selectedIds[episodeId] ?? [],
      isSelected: (episodeId, tmdbEpisodeId) =>
        (selectedIds[episodeId] ?? []).includes(tmdbEpisodeId),
      toggle,
      clear,
    }),
    [selectedIds, toggle, clear],
  )

  return (
    <TmdbChoiceSelectionContext.Provider value={value}>
      {children}
    </TmdbChoiceSelectionContext.Provider>
  )
}
