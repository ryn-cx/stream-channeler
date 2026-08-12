// TODO: Validate
import type { VisibilityState } from "@tanstack/react-table"
import { usePersistedJsonState } from "@/hooks/usePersistedState"

// Every channel scope (owned, favorites, public, all) lists the same columns, so
// they share one stored visibility state rather than each remembering its own.
const CHANNEL_COLUMN_VISIBILITY_KEY = "channels-column-visibility"

// TODO: Validate
export function useChannelColumnVisibility() {
  return usePersistedJsonState<VisibilityState>(CHANNEL_COLUMN_VISIBILITY_KEY, {
    id: false,
  })
}
