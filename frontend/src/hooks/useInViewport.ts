// TODO: Validate
import { type RefObject, useEffect, useState } from "react"

// TODO: Validate
export function useInViewport(
  target: RefObject<HTMLElement | null>,
  rootMargin = "600px",
): boolean {
  const [inViewport, setInViewport] = useState(false)

  useEffect(() => {
    if (inViewport) return
    const element = target.current
    if (!element) return

    const observer = new IntersectionObserver(
      (entries) => {
        if (entries.some((entry) => entry.isIntersecting)) {
          setInViewport(true)
          observer.disconnect()
        }
      },
      { rootMargin },
    )
    observer.observe(element)
    return () => observer.disconnect()
  }, [target, rootMargin, inViewport])

  return inViewport
}
