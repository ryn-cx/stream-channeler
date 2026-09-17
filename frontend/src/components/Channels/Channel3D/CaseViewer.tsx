// TODO: Validate
import { X } from "lucide-react"
import { useEffect, useRef } from "react"
import * as THREE from "three"
import {
  createBackTexture,
  createCaseCanvas,
  type StoreTitle,
} from "./caseTexture"

// TODO: Validate
const regionTexture = (
  canvas: HTMLCanvasElement,
  x: number,
  y: number,
  width: number,
  height: number,
) => {
  const texture = new THREE.CanvasTexture(canvas)
  texture.colorSpace = THREE.SRGBColorSpace
  texture.anisotropy = 8
  texture.offset.set(x / 256, y / 256)
  texture.repeat.set(width / 256, height / 256)
  return texture
}

// TODO: Validate
const loadImage = (url: string | null) =>
  new Promise<HTMLImageElement | null>((resolve) => {
    if (!url) {
      resolve(null)
      return
    }
    const image = new Image()
    image.crossOrigin = "anonymous"
    image.referrerPolicy = "no-referrer"
    image.onload = () => resolve(image)
    image.onerror = () => resolve(null)
    image.src = url
  })

// TODO: Validate
export function CaseViewer({
  title,
  onClose,
}: {
  title: StoreTitle
  onClose: () => void
}) {
  const containerRef = useRef<HTMLDivElement>(null)
  const overlayRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const overlay = overlayRef.current
    if (!overlay) return
    // TODO: Validate
    const swallow = (event: Event) => event.stopPropagation()
    // TODO: Validate
    const block = (event: Event) => event.preventDefault()
    overlay.addEventListener("mousedown", swallow)
    overlay.addEventListener("pointerdown", swallow)
    overlay.addEventListener("dragstart", block)
    return () => {
      overlay.removeEventListener("mousedown", swallow)
      overlay.removeEventListener("pointerdown", swallow)
      overlay.removeEventListener("dragstart", block)
    }
  }, [])

  useEffect(() => {
    const container = containerRef.current
    if (!container) return

    let disposed = false
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true })
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
    renderer.setSize(container.clientWidth, container.clientHeight)
    renderer.domElement.draggable = false
    renderer.domElement.style.touchAction = "none"
    renderer.domElement.style.userSelect = "none"
    container.appendChild(renderer.domElement)

    const scene = new THREE.Scene()
    const camera = new THREE.PerspectiveCamera(
      38,
      container.clientWidth / container.clientHeight,
      0.1,
      50,
    )
    camera.position.set(0, 0, 4.4)

    scene.add(new THREE.AmbientLight(0xffffff, 1.5))
    const key = new THREE.DirectionalLight(0xffffff, 2.2)
    key.position.set(2.5, 3, 4)
    scene.add(key)
    const rim = new THREE.DirectionalLight(0x9ad7ff, 1.4)
    rim.position.set(-3, -1, -4)
    scene.add(rim)

    const leftEdge = new THREE.MeshStandardMaterial({ roughness: 0.5 })
    const rightEdge = new THREE.MeshStandardMaterial({ roughness: 0.5 })
    const top = new THREE.MeshStandardMaterial({ roughness: 0.5 })
    const bottom = new THREE.MeshStandardMaterial({ roughness: 0.5 })
    const front = new THREE.MeshStandardMaterial({ roughness: 0.42 })
    const back = new THREE.MeshStandardMaterial({ roughness: 0.42 })
    const materials = [rightEdge, leftEdge, top, bottom, front, back]

    const mesh = new THREE.Mesh(
      new THREE.BoxGeometry(1.35, 1.9, 0.15),
      materials,
    )
    mesh.rotation.set(0, -0.5, 0)
    scene.add(mesh)

    const paint = async () => {
      const [cover, backdrop] = await Promise.all([
        loadImage(title.fullImageUrl ?? title.imageUrl),
        loadImage(title.backImageUrl),
      ])
      if (disposed) return
      const caseCanvas = createCaseCanvas(title, cover, 5)
      front.map = regionTexture(caseCanvas, 0, 32, 168, 224)
      front.needsUpdate = true
      leftEdge.map = regionTexture(caseCanvas, 168, 32, 24, 224)
      leftEdge.needsUpdate = true
      rightEdge.map = regionTexture(caseCanvas, 192, 32, 24, 224)
      rightEdge.needsUpdate = true
      top.map = regionTexture(caseCanvas, 0, 16, 168, 16)
      top.needsUpdate = true
      bottom.map = regionTexture(caseCanvas, 0, 0, 168, 16)
      bottom.needsUpdate = true
      back.map = createBackTexture(title, backdrop, cover)
      back.needsUpdate = true
    }
    paint()

    let lastX = 0
    let lastY = 0
    let spin = 0.0045
    let distance = 4.4
    let pinch = 0
    const pointers = new Map<number, { x: number; y: number }>()

    // TODO: Validate
    const zoom = (next: number) => {
      distance = THREE.MathUtils.clamp(next, 1.9, 9)
      camera.position.z = distance
    }

    // TODO: Validate
    const pinchSpan = () => {
      const [first, second] = [...pointers.values()]
      return Math.hypot(first.x - second.x, first.y - second.y)
    }

    // TODO: Validate
    const onPointerDown = (event: PointerEvent) => {
      event.preventDefault()
      spin = 0
      pointers.set(event.pointerId, { x: event.clientX, y: event.clientY })
      lastX = event.clientX
      lastY = event.clientY
      if (pointers.size === 2) pinch = pinchSpan()
      renderer.domElement.setPointerCapture(event.pointerId)
    }

    // TODO: Validate
    const onPointerMove = (event: PointerEvent) => {
      if (!pointers.has(event.pointerId)) return
      pointers.set(event.pointerId, { x: event.clientX, y: event.clientY })

      if (pointers.size >= 2) {
        const span = pinchSpan()
        if (pinch > 0 && span > 0) zoom(distance * (pinch / span))
        pinch = span
        return
      }

      mesh.rotation.y += (event.clientX - lastX) * 0.01
      mesh.rotation.x = THREE.MathUtils.clamp(
        mesh.rotation.x + (event.clientY - lastY) * 0.01,
        -Math.PI / 2,
        Math.PI / 2,
      )
      lastX = event.clientX
      lastY = event.clientY
    }

    // TODO: Validate
    const onPointerUp = (event: PointerEvent) => {
      pointers.delete(event.pointerId)
      pinch = 0
      const remaining = [...pointers.values()][0]
      if (remaining) {
        lastX = remaining.x
        lastY = remaining.y
      }
      renderer.domElement.releasePointerCapture(event.pointerId)
    }

    // TODO: Validate
    const onWheel = (event: WheelEvent) => {
      event.preventDefault()
      spin = 0
      zoom(distance + event.deltaY * 0.0022)
    }

    renderer.domElement.addEventListener("pointerdown", onPointerDown)
    renderer.domElement.addEventListener("pointermove", onPointerMove)
    renderer.domElement.addEventListener("pointerup", onPointerUp)
    renderer.domElement.addEventListener("pointercancel", onPointerUp)
    renderer.domElement.addEventListener("wheel", onWheel, { passive: false })

    // TODO: Validate
    const resize = () => {
      if (!container.clientWidth || !container.clientHeight) return
      camera.aspect = container.clientWidth / container.clientHeight
      camera.updateProjectionMatrix()
      renderer.setSize(container.clientWidth, container.clientHeight)
    }
    const observer = new ResizeObserver(resize)
    observer.observe(container)

    let frame = 0
    // TODO: Validate
    const tick = () => {
      if (disposed) return
      frame = requestAnimationFrame(tick)
      mesh.rotation.y += spin
      renderer.render(scene, camera)
    }
    tick()

    return () => {
      disposed = true
      cancelAnimationFrame(frame)
      observer.disconnect()
      renderer.domElement.removeEventListener("pointerdown", onPointerDown)
      renderer.domElement.removeEventListener("pointermove", onPointerMove)
      renderer.domElement.removeEventListener("pointerup", onPointerUp)
      renderer.domElement.removeEventListener("pointercancel", onPointerUp)
      renderer.domElement.removeEventListener("wheel", onWheel)
      mesh.geometry.dispose()
      for (const material of materials) {
        material.map?.dispose()
        material.dispose()
      }
      renderer.dispose()
      renderer.domElement.remove()
    }
  }, [title])

  useEffect(() => {
    // TODO: Validate
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.code === "Escape") onClose()
    }
    window.addEventListener("keydown", onKeyDown)
    return () => window.removeEventListener("keydown", onKeyDown)
  }, [onClose])

  return (
    <div
      ref={overlayRef}
      className="absolute inset-0 z-20 flex select-none flex-col items-center justify-center bg-black/80 backdrop-blur-sm"
    >
      <button
        type="button"
        onClick={onClose}
        className="absolute right-4 top-4 flex items-center gap-2 rounded-full bg-black/60 px-4 py-2 text-sm text-white/80 hover:text-white"
      >
        <X className="size-4" />
        Back to the shelves
      </button>

      <div
        ref={containerRef}
        className="h-[70vh] w-full max-w-4xl cursor-grab touch-none active:cursor-grabbing"
      />

      <div className="flex flex-col items-center gap-2 pb-6 text-center">
        <div className="text-lg font-semibold text-white">{title.name}</div>
        <div className="text-xs text-white/50">
          Drag to spin · Scroll or pinch to zoom · Esc to put it back
        </div>
        {title.url && (
          <a
            href={title.url}
            target="_blank"
            rel="noreferrer"
            className="mt-1 rounded-full border border-emerald-300/40 px-5 py-2 text-sm font-medium text-emerald-200 hover:bg-emerald-300/10"
          >
            Take it to the counter
          </a>
        )}
      </div>
    </div>
  )
}
