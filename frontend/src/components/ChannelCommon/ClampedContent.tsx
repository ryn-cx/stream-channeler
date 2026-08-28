// TODO: Validate
import { type ReactNode, useLayoutEffect, useRef, useState } from "react"

interface ClampedContentProps {
  children: ReactNode
  className?: string
  lines?: 4 | 5
}

// TODO: Validate
/**
 * Content held to four lines until it is asked for in full.
 *
 * A description runs as long as the site that wrote it cared to, which is what
 * leaves a record's own line taller than everything around it. The button is
 * only there when there is more to read.
 */
export function ClampedContent({
  children,
  className,
  lines = 4,
}: ClampedContentProps) {
  const [expanded, setExpanded] = useState(false)
  const [clipped, setClipped] = useState(false)
  const contentRef = useRef<HTMLDivElement>(null)

  useLayoutEffect(() => {
    const element = contentRef.current
    if (!element) return
    setClipped(element.scrollHeight > element.clientHeight)
  }, [])

  return (
    <div className={className}>
      <div
        ref={contentRef}
        className={
          expanded ? undefined : { 4: "line-clamp-4", 5: "line-clamp-5" }[lines]
        }
      >
        {children}
      </div>
      {(clipped || expanded) && (
        <button
          type="button"
          className="text-xs text-primary hover:underline"
          onClick={() => setExpanded(!expanded)}
        >
          {expanded ? "Show less" : "Show more"}
        </button>
      )}
    </div>
  )
}
