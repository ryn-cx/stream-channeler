// TODO: Validate
import { type ReactNode, useLayoutEffect, useRef, useState } from "react"

interface ClampedContentProps {
  children: ReactNode
  className?: string
  lines?: 4 | 5
}

// TODO: Validate
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
          {expanded ? "Title less" : "Title more"}
        </button>
      )}
    </div>
  )
}
