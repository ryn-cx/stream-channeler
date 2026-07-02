// TODO: Validate
import { type RefObject, useEffect, useState } from "react"

import type { MoveDirection } from "@/components/ChannelCommon/EpisodeCard"

/** Tailwind classes for the responsive episode card grid used by the
 * channel detail page. */
export const EPISODE_GRID_CLASSES =
  "grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5 3xl:grid-cols-6 4xl:grid-cols-7 5xl:grid-cols-8 gap-4 items-start"

/** Measure the number of cards on the first row of an episode grid so vertical
 * reorder moves can step by a full row at a time. */
export function useColumnCount(ref: RefObject<HTMLDivElement | null>): number {
  const [columnCount, setColumnCount] = useState(1)

  useEffect(() => {
    const grid = ref.current
    if (!grid) return
    const measure = () => {
      const children = Array.from(grid.children) as HTMLElement[]
      if (children.length === 0) return
      const firstTop = children[0].offsetTop
      let count = 0
      for (const child of children) {
        if (child.offsetTop !== firstTop) break
        count++
      }
      setColumnCount(Math.max(count, 1))
    }
    measure()
    const observer = new ResizeObserver(measure)
    observer.observe(grid)
    return () => observer.disconnect()
  }, [ref])

  return columnCount
}

/** Resolve an arrow-key reorder direction into a target index, given the
 * current grid layout. Callers pass the result to their swap/move helper. */
export function resolveArrowMove(
  index: number,
  direction: MoveDirection,
  columnCount: number,
  length: number,
):
  | { kind: "noop" }
  | { kind: "move"; to: number }
  | { kind: "swap"; to: number } {
  if (direction === "first") return { kind: "move", to: 0 }
  if (direction === "last") return { kind: "move", to: length - 1 }
  const offset =
    direction === "left"
      ? -1
      : direction === "right"
        ? 1
        : direction === "up"
          ? -columnCount
          : columnCount
  const target = index + offset
  if (target < 0 || target >= length) return { kind: "noop" }
  return { kind: "swap", to: target }
}
