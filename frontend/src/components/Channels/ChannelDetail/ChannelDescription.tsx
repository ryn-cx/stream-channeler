// TODO: Validate
import { useEffect, useRef, useState } from "react"

import type { ChannelAdminOutput, ChannelOutput } from "@/client"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogBody,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"

interface ChannelDescriptionProps {
  channel: ChannelOutput | ChannelAdminOutput
}

export function ChannelDescription({ channel }: ChannelDescriptionProps) {
  const [open, setOpen] = useState(false)
  const [isTruncated, setIsTruncated] = useState(false)
  const textRef = useRef<HTMLParagraphElement>(null)

  const description = channel.description

  useEffect(() => {
    const element = textRef.current
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
    <div className="-mt-2 flex flex-col items-start gap-1 px-[4%] pb-4">
      <p
        ref={textRef}
        className="line-clamp-2 max-w-3xl text-sm text-muted-foreground"
      >
        {description}
      </p>
      {isTruncated && (
        <Button
          variant="link"
          className="h-auto p-0 text-sm"
          onClick={() => setOpen(true)}
        >
          Read more
        </Button>
      )}

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{channel.name ?? "Channel"}</DialogTitle>
          </DialogHeader>
          <DialogBody>
            <p className="text-sm whitespace-pre-wrap text-muted-foreground">
              {description}
            </p>
          </DialogBody>
        </DialogContent>
      </Dialog>
    </div>
  )
}
