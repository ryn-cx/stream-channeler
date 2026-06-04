// TODO: Validate
import { useCallback, useState } from "react"

/**
 * Like useState but persists the value to localStorage.
 * Falls back to defaultValue if nothing is stored or the stored value is invalid.
 */
export function usePersistedState<T extends string>(
  key: string,
  defaultValue: T,
): [T, (value: T) => void] {
  const [value, setValue] = useState<T>(() => {
    const stored = localStorage.getItem(key)
    return stored !== null ? (stored as T) : defaultValue
  })

  const setPersisted = (newValue: T) => {
    localStorage.setItem(key, newValue)
    setValue(newValue)
  }

  return [value, setPersisted]
}

/**
 * Like useState but persists a JSON-serializable value to localStorage,
 * mirroring how table sorting is persisted in DataTable: the stored value is
 * read once on init and written on every change. The setter accepts either a
 * new value or an updater function, so it is compatible with TanStack Table's
 * `OnChangeFn` (e.g. `onColumnVisibilityChange`).
 *
 * Falls back to defaultValue if nothing is stored or the stored value is invalid.
 */
export function usePersistedJsonState<T>(
  key: string,
  defaultValue: T,
): [T, (updater: T | ((previous: T) => T)) => void] {
  const [value, setValue] = useState<T>(() => {
    const stored = localStorage.getItem(key)
    if (stored !== null) {
      try {
        return JSON.parse(stored) as T
      } catch {
        // Ignore malformed values and fall back to the default.
      }
    }
    return defaultValue
  })

  const setPersisted = useCallback(
    (updater: T | ((previous: T) => T)) => {
      setValue((previous) => {
        const next =
          typeof updater === "function"
            ? (updater as (previous: T) => T)(previous)
            : updater
        localStorage.setItem(key, JSON.stringify(next))
        return next
      })
    },
    [key],
  )

  return [value, setPersisted]
}
