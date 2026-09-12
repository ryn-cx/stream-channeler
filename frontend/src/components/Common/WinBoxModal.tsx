// TODO: Validate
import { type ReactNode, useEffect, useRef, useState } from "react"
import { createPortal } from "react-dom"
import WinBox from "winbox/src/js/winbox.js"
import "winbox/dist/css/winbox.min.css"
import { cn } from "@/lib/utils"

interface WinBoxModalProps {
  open: boolean
  title: string
  onClose: () => void
  width?: string
  height?: string
  className?: string
  children: ReactNode
}

// TODO: Validate
export function WinBoxModal({
  open,
  title,
  onClose,
  width = "70%",
  height = "80%",
  className,
  children,
}: WinBoxModalProps) {
  const [mount, setMount] = useState<HTMLDivElement | null>(null)
  const onCloseRef = useRef(onClose)
  const titleRef = useRef(title)
  const winBoxRef = useRef<WinBox | null>(null)

  useEffect(() => {
    onCloseRef.current = onClose
  }, [onClose])

  useEffect(() => {
    titleRef.current = title
    winBoxRef.current?.setTitle(title)
  }, [title])

  useEffect(() => {
    if (!open) {
      return
    }
    const host = document.createElement("div")
    host.style.height = "100%"
    let unmounting = false
    let closed = false
    const winBox = new WinBox({
      title: titleRef.current,
      mount: host,
      width,
      height,
      x: "center",
      y: "center",
      background: "var(--primary)",
      index: 50,
      onclose: () => {
        closed = true
        winBoxRef.current = null
        if (!unmounting) {
          onCloseRef.current()
        }
        return false
      },
    })
    winBoxRef.current = winBox
    setMount(host)
    return () => {
      unmounting = true
      winBoxRef.current = null
      setMount(null)
      if (!closed) {
        winBox.close(true)
      }
    }
  }, [open, width, height])

  if (!mount) {
    return null
  }
  return createPortal(
    <div
      className={cn(
        "h-full overflow-y-auto bg-background text-foreground",
        className,
      )}
    >
      {children}
    </div>,
    mount,
  )
}
