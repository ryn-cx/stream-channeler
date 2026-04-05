// TODO: Validate
import { useState } from "react"

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
