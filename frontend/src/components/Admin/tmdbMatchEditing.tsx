// TODO: Validate
import { createContext, useContext } from "react"

import type { UnmatchedEpisodeOutput } from "@/client"

const OpenEpisodeEditorContext = createContext<
  ((episode: UnmatchedEpisodeOutput) => void) | null
>(null)

export const OpenEpisodeEditorProvider = OpenEpisodeEditorContext.Provider

// TODO: Validate
export function useOpenEpisodeEditor() {
  return useContext(OpenEpisodeEditorContext)
}
