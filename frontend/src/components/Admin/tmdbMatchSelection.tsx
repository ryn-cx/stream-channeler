// TODO: Validate
import {
  createContext,
  type ReactNode,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react"

import type { TmdbMatchRow } from "./tmdbMatchColumns"

export const MATCH_KINDS = [
  { kind: "name", label: "Best name match", field: "best_match" },
  {
    kind: "season_episode",
    label: "Episode Number → Episode Number",
    field: "season_episode_match",
  },
  {
    kind: "absolute",
    label: "Absolute Number → Absolute Number",
    field: "absolute_number_match",
  },
  {
    kind: "episode_absolute",
    label: "Episode Number → Absolute Number",
    field: "episode_number_absolute_match",
  },
  {
    kind: "description_embedding",
    label: "Description (embedding)",
    field: "description_embedding_match",
  },
  {
    kind: "description_blended",
    label: "Description (blended)",
    field: "description_blended_match",
  },
  {
    kind: "title_embedding",
    label: "Title (embedding)",
    field: "title_embedding_match",
  },
  {
    kind: "title_blended",
    label: "Title (blended)",
    field: "title_blended_match",
  },
] as const

export type MatchKind = (typeof MATCH_KINDS)[number]["kind"]
export type MatchField = (typeof MATCH_KINDS)[number]["field"]

interface TmdbMatchSelection {
  selectedIds: string[]
  isSelected: (episodeId: string) => boolean
  toggle: (episodeId: string, extendFromAnchor: boolean) => void
  clear: () => void
  selectedRows: TmdbMatchRow[]
}

const TmdbMatchSelectionContext = createContext<TmdbMatchSelection | null>(null)

// TODO: Validate
export function useTmdbMatchSelection() {
  return useContext(TmdbMatchSelectionContext)
}

// TODO: Validate
export function TmdbMatchSelectionProvider({
  rows,
  children,
}: {
  rows: TmdbMatchRow[]
  children: ReactNode
}) {
  const [selectedIds, setSelectedIds] = useState<string[]>([])
  const [anchorId, setAnchorId] = useState<string | null>(null)

  const rowIds = useMemo(() => rows.map((row) => row.episode.id), [rows])

  useEffect(() => {
    setSelectedIds((previous) => {
      const kept = previous.filter((id) => rowIds.includes(id))
      return kept.length === previous.length ? previous : kept
    })
  }, [rowIds])

  const toggle = useCallback(
    (episodeId: string, extendFromAnchor: boolean) => {
      const anchorIndex = anchorId === null ? -1 : rowIds.indexOf(anchorId)
      const clickedIndex = rowIds.indexOf(episodeId)
      if (!extendFromAnchor || anchorIndex === -1 || clickedIndex === -1) {
        setAnchorId(episodeId)
        setSelectedIds((previous) =>
          previous.includes(episodeId)
            ? previous.filter((id) => id !== episodeId)
            : [...previous, episodeId],
        )
        return
      }

      const start = Math.min(anchorIndex, clickedIndex)
      const end = Math.max(anchorIndex, clickedIndex)
      const range = rowIds.slice(start, end + 1)
      setSelectedIds((previous) => [
        ...previous.filter((id) => !range.includes(id)),
        ...range,
      ])
    },
    [anchorId, rowIds],
  )

  const value = useMemo<TmdbMatchSelection>(() => {
    const selected = new Set(selectedIds)
    return {
      selectedIds,
      isSelected: (episodeId: string) => selected.has(episodeId),
      toggle,
      clear: () => {
        setSelectedIds([])
        setAnchorId(null)
      },
      selectedRows: rows.filter((row) => selected.has(row.episode.id)),
    }
  }, [rows, selectedIds, toggle])

  return (
    <TmdbMatchSelectionContext.Provider value={value}>
      {children}
    </TmdbMatchSelectionContext.Provider>
  )
}
