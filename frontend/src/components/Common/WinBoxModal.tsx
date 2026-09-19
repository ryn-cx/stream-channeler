// TODO: Validate
import { type ReactNode, useEffect, useRef, useState } from "react"
import { createPortal } from "react-dom"
import WinBox from "winbox/src/js/winbox.js"
import "winbox/dist/css/winbox.min.css"
import { cn } from "@/lib/utils"

// TODO: Validate
const nextWinBoxIndex = () => {
  const open = Array.from(document.querySelectorAll<HTMLElement>(".winbox"))
  const highest = open.reduce(
    (top, element) => Math.max(top, Number(element.style.zIndex) || 0),
    49,
  )
  return highest + 1
}

interface WinBoxModalProps {
  open: boolean
  title: string
  onClose: () => void
  width?: string
  height?: string
  autoHeight?: boolean
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
  autoHeight = false,
  className,
  children,
}: WinBoxModalProps) {
  const [mount, setMount] = useState<HTMLDivElement | null>(null)
  const onCloseRef = useRef(onClose)
  const titleRef = useRef(title)
  const winBoxRef = useRef<WinBox | null>(null)
  const contentRef = useRef<HTMLDivElement | null>(null)

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
      index: nextWinBoxIndex(),
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

  useEffect(() => {
    const content = contentRef.current
    if (!autoHeight || !mount || !content) {
      return
    }
    // TODO: Validate
    const fit = () => {
      const winBox = winBoxRef.current
      if (!winBox?.dom || !winBox.body) {
        return
      }
      const chrome = winBox.dom.offsetHeight - winBox.body.clientHeight
      const wanted = Math.min(
        content.offsetHeight + chrome,
        Math.round(window.innerHeight * 0.9),
      )
      if (Math.abs(wanted - winBox.dom.offsetHeight) < 2) {
        return
      }
      winBox.resize(winBox.dom.offsetWidth, wanted).move("center", "center")
    }
    const observer = new ResizeObserver(fit)
    observer.observe(content)
    window.addEventListener("resize", fit)
    return () => {
      observer.disconnect()
      window.removeEventListener("resize", fit)
    }
  }, [autoHeight, mount])

  if (!mount) {
    return null
  }
  return createPortal(
    <div
      ref={contentRef}
      className={cn(
        autoHeight ? "h-max" : "h-full overflow-y-auto",
        "bg-background text-foreground",
        className,
      )}
    >
      {children}
    </div>,
    mount,
  )
}
