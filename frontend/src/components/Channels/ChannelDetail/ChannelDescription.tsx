// TODO: Validate
import { FileText } from "lucide-react"
import Markdown, { type Components } from "react-markdown"

import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogBody,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip"
import { cn } from "@/lib/utils"

interface ChannelDescriptionProps {
  channel: { name?: string | null; description?: string | null }
  className?: string
}

const INTERNAL_HOSTS = ["streamchanneler.com"]

// TODO: Validate
function isInternalHref(href: string | undefined): boolean {
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

// Some AI generated  stuff to fix the missing styles on markdown text.
const markdownComponents: Components = {
  a: ({ href, children }) =>
    isInternalHref(href) ? (
      <a
        href={href}
        target="_blank"
        rel="noopener noreferrer"
        className="underline hover:text-foreground"
      >
        {children}
      </a>
    ) : null,
  h1: ({ children }) => (
    <h1 className="mt-4 mb-2 text-xl font-semibold text-foreground first:mt-0">
      {children}
    </h1>
  ),
  h2: ({ children }) => (
    <h2 className="mt-4 mb-2 text-lg font-semibold text-foreground first:mt-0">
      {children}
    </h2>
  ),
  h3: ({ children }) => (
    <h3 className="mt-3 mb-1 text-base font-semibold text-foreground first:mt-0">
      {children}
    </h3>
  ),
  h4: ({ children }) => (
    <h4 className="mt-3 mb-1 text-sm font-semibold text-foreground first:mt-0">
      {children}
    </h4>
  ),
  ul: ({ children }) => (
    <ul className="list-inside list-disc space-y-1">{children}</ul>
  ),
  ol: ({ children }) => (
    <ol className="list-inside list-decimal space-y-1">{children}</ol>
  ),
  blockquote: ({ children }) => (
    <blockquote className="border-l-2 pl-3 italic">{children}</blockquote>
  ),
}

const markdownStyles =
  "[&_code]:rounded [&_code]:bg-muted [&_code]:px-1.5 [&_code]:py-0.5 [&_code]:text-xs"

// TODO: Validate
export function ChannelDescription({
  channel,
  className,
}: ChannelDescriptionProps) {
  if (!channel.description) return null

  return (
    <Dialog>
      <Tooltip>
        <TooltipTrigger asChild>
          <DialogTrigger asChild>
            <Button variant="ghost" size="icon" className={className}>
              <FileText className="size-4" />
              <span className="sr-only">Description</span>
            </Button>
          </DialogTrigger>
        </TooltipTrigger>
        <TooltipContent>Description</TooltipContent>
      </Tooltip>
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
          <Markdown components={markdownComponents}>
            {channel.description}
          </Markdown>
        </DialogBody>
      </DialogContent>
    </Dialog>
  )
}
