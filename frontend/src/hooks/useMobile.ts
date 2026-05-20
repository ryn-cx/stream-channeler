// TODO: Validate
import * as React from "react"

const NARROW_VIEWPORT_BREAKPOINT = 768

/**
 * Returns true when the viewport is narrower than the mobile breakpoint.
 * Use this for layout decisions that should adapt to the available width —
 * e.g. switching to an overlay sidebar when a desktop window is shrunk.
 */
export function useIsNarrowViewport() {
  const [isNarrow, setIsNarrow] = React.useState<boolean | undefined>(undefined)

  React.useEffect(() => {
    const mql = window.matchMedia(
      `(max-width: ${NARROW_VIEWPORT_BREAKPOINT - 1}px)`,
    )
    const onChange = () => {
      setIsNarrow(window.innerWidth < NARROW_VIEWPORT_BREAKPOINT)
    }
    mql.addEventListener("change", onChange)
    setIsNarrow(window.innerWidth < NARROW_VIEWPORT_BREAKPOINT)
    return () => mql.removeEventListener("change", onChange)
  }, [])

  return !!isNarrow
}

/**
 * Returns true when the primary input is a touch / coarse pointer (phones,
 * tablets), regardless of viewport width. Use this when behavior should
 * depend on the device type, not the window size — e.g. a narrow desktop
 * window should keep the desktop interaction model.
 */
export function useIsTouchDevice() {
  const [isTouch, setIsTouch] = React.useState<boolean | undefined>(undefined)

  React.useEffect(() => {
    const mql = window.matchMedia("(pointer: coarse)")
    const onChange = () => setIsTouch(mql.matches)
    mql.addEventListener("change", onChange)
    setIsTouch(mql.matches)
    return () => mql.removeEventListener("change", onChange)
  }, [])

  return !!isTouch
}
