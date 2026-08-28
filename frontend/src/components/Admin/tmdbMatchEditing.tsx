// TODO: Validate
import { createContext, useContext } from "react"

import type { TmdbMatchRow } from "./tmdbMatchColumns"

const OpenEpisodeEditorContext = createContext<
  ((episode: TmdbMatchRow) => void) | null
>(null)

export const OpenEpisodeEditorProvider = OpenEpisodeEditorContext.Provider

// TODO: Validate
export function useOpenEpisodeEditor() {
  return useContext(OpenEpisodeEditorContext)
}
