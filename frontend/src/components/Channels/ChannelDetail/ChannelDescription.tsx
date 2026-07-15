// TODO: Validate
import { type ReactNode, useEffect, useRef, useState } from "react"
import Markdown, { type Components } from "react-markdown"

import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogBody,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { cn } from "@/lib/utils"

interface ChannelDescriptionProps {
  channel: { name?: string | null; description?: string | null }
  className?: string
}

const INTERNAL_HOSTS = ["streamchanneler.com"]

// Links to Stream Channeler (or relative/same-origin links) are kept; any other
// external link is rendered as plain text so descriptions can't link elsewhere.
function _isInternalHref(href: string | undefined): boolean {
  if (!href) return false
  try {
    const url = new URL(href, window.location.origin)
    if (url.protocol !== "http:" && url.protocol !== "https:") return false
    const host = url.hostname.toLowerCase()
    return (
      host === window.location.hostname ||
      INTERNAL_HOSTS.some(
        (internal) => host === internal || host.endsWith(`.${internal}`),
      )
    )
  } catch {
    return false
  }
}

function InlineText({ children }: { children?: ReactNode }) {
  return <span>{children} </span>
}

// The preview flattens every block element and line break to inline text so the
// clamped last line is always full-width. That keeps "Read more" flush against
// where the text ends instead of leaving a gap after a hard line break.
const previewComponents: Components = {
  a: markdownComponents.a,
  p: InlineText,
  h1: InlineText,
  h2: InlineText,
  h3: InlineText,
  h4: InlineText,
  h5: InlineText,
  h6: InlineText,
  blockquote: InlineText,
  li: InlineText,
  ul: ({ children }) => <span>{children}</span>,
  ol: ({ children }) => <span>{children}</span>,
  br: () => <span> </span>,
  img: () => null,
}

// Shared code-block styling for both the clamped preview and the full modal.
const markdownStyles =
  "[&_code]:rounded [&_code]:bg-muted [&_code]:px-1.5 [&_code]:py-0.5 [&_code]:text-xs"

export function ChannelDescription({
  channel,
  className,
}: ChannelDescriptionProps) {
  const [open, setOpen] = useState(false)
  const [isTruncated, setIsTruncated] = useState(false)
  const previewRef = useRef<HTMLDivElement>(null)

  const description = channel.description

  useEffect(() => {
    const element = previewRef.current
    if (!element) return
    const check = () => {
      setIsTruncated(element.scrollHeight > element.clientHeight)
    }
    check()
    const observer = new ResizeObserver(check)
    observer.observe(element)
    return () => observer.disconnect()
  }, [])

  if (!description) return null

  return (
    <div className={className}>
      <div className="relative max-w-3xl">
        <div
          ref={previewRef}
          className={cn(
            "line-clamp-2 text-sm text-muted-foreground",
            markdownStyles,
          )}
        >
          <Markdown components={previewComponents}>{description}</Markdown>
        </div>
        {isTruncated && (
          <Button
            variant="link"
            className="absolute right-0 bottom-0 h-5 bg-background p-0 text-sm"
            onClick={() => setOpen(true)}
          >
            {/* Fade the last line out before the button so text doesn't collide. */}
            <span
              aria-hidden
              className="pointer-events-none absolute top-0 right-full h-full w-8 bg-linear-to-l from-background to-transparent"
            />
            Read more
          </Button>
        )}
      </div>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{channel.name ?? "Channel"}</DialogTitle>
          </DialogHeader>
          <DialogBody
            className={cn(
              "text-sm text-muted-foreground [&_ol]:my-2 [&_p]:my-2 [&_ul]:my-2",
              markdownStyles,
            )}
          >
            <Markdown components={markdownComponents}>{description}</Markdown>
          </DialogBody>
        </DialogContent>
      </Dialog>
    </div>
  )
}
