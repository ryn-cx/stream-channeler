// TODO: Validate
import { ChevronsDown, LogOut } from "lucide-react"
import { useRef, useState } from "react"
import type { VideoStore } from "./videoStore"

const STICK_RADIUS = 56

// TODO: Validate
const findTouch = (touches: React.TouchList, id: number) => {
  for (let index = 0; index < touches.length; index++) {
    if (touches[index].identifier === id) return touches[index]
  }
  return null
}

// TODO: Validate
export function TouchControls({ store }: { store: VideoStore | null }) {
  const [knob, setKnob] = useState({ x: 0, y: 0 })
  const [crouching, setCrouching] = useState(false)
  const stickRef = useRef<HTMLDivElement>(null)
  const stickTouch = useRef<{ id: number; x: number; y: number } | null>(null)
  const lookTouch = useRef<{
    id: number
    x: number
    y: number
    travel: number
    at: number
  } | null>(null)

  // TODO: Validate
  const steer = (touch: React.Touch) => {
    const base = stickRef.current?.getBoundingClientRect()
    if (!base) return
    const deltaX = touch.clientX - (base.left + base.width / 2)
    const deltaY = touch.clientY - (base.top + base.height / 2)
    const distance = Math.hypot(deltaX, deltaY)
    const scale = distance > STICK_RADIUS ? STICK_RADIUS / distance : 1
    const knobX = deltaX * scale
    const knobY = deltaY * scale
    setKnob({ x: knobX, y: knobY })
    store?.setMove(
      knobX / STICK_RADIUS,
      -knobY / STICK_RADIUS,
      distance > STICK_RADIUS * 0.85,
    )
  }

  // TODO: Validate
  const onStickStart = (event: React.TouchEvent) => {
    const touch = event.changedTouches[0]
    stickTouch.current = {
      id: touch.identifier,
      x: touch.clientX,
      y: touch.clientY,
    }
    steer(touch)
  }

  // TODO: Validate
  const onStickMove = (event: React.TouchEvent) => {
    const origin = stickTouch.current
    if (!origin) return
    const touch = findTouch(event.changedTouches, origin.id)
    if (!touch) return
    steer(touch)
  }

  // TODO: Validate
  const onStickEnd = () => {
    stickTouch.current = null
    setKnob({ x: 0, y: 0 })
    store?.setMove(0, 0, false)
  }

  // TODO: Validate
  const onLookStart = (event: React.TouchEvent) => {
    const touch = event.changedTouches[0]
    lookTouch.current = {
      id: touch.identifier,
      x: touch.clientX,
      y: touch.clientY,
      travel: 0,
      at: Date.now(),
    }
  }

  // TODO: Validate
  const onLookMove = (event: React.TouchEvent) => {
    const previous = lookTouch.current
    if (!previous) return
    const touch = findTouch(event.changedTouches, previous.id)
    if (!touch) return
    const deltaX = touch.clientX - previous.x
    const deltaY = touch.clientY - previous.y
    store?.look(deltaX, deltaY)
    previous.x = touch.clientX
    previous.y = touch.clientY
    previous.travel += Math.hypot(deltaX, deltaY)
  }

  // TODO: Validate
  const onLookEnd = (event: React.TouchEvent) => {
    const previous = lookTouch.current
    if (!previous) return
    const touch = findTouch(event.changedTouches, previous.id)
    lookTouch.current = null
    if (!touch || previous.travel > 12 || Date.now() - previous.at > 400) return
    store?.focusAt(touch.clientX, touch.clientY)
  }

  // TODO: Validate
  const toggleCrouch = () => {
    setCrouching((previous) => {
      store?.setCrouch(!previous)
      return !previous
    })
  }

  return (
    <div className="absolute inset-0 touch-none">
      <div
        className="absolute inset-0"
        onTouchStart={onLookStart}
        onTouchMove={onLookMove}
        onTouchEnd={onLookEnd}
        onTouchCancel={onLookEnd}
      />

      <div
        className="absolute bottom-10 left-8 flex size-36 items-center justify-center rounded-full"
        onTouchStart={onStickStart}
        onTouchMove={onStickMove}
        onTouchEnd={onStickEnd}
        onTouchCancel={onStickEnd}
      >
        <div
          ref={stickRef}
          className="pointer-events-none relative size-32 rounded-full border border-white/25 bg-black/35 backdrop-blur"
        >
          <div
            className="absolute left-1/2 top-1/2 size-14 rounded-full border border-white/45 bg-white/30"
            style={{
              transform: `translate(calc(-50% + ${knob.x * 0.55}px), calc(-50% + ${knob.y * 0.55}px))`,
            }}
          />
        </div>
      </div>

      <div className="absolute bottom-8 right-6 flex flex-col items-end gap-3">
        <button
          type="button"
          onClick={toggleCrouch}
          className={`flex items-center gap-2 rounded-full px-5 py-3 text-sm font-medium backdrop-blur ${
            crouching ? "bg-white/85 text-black" : "bg-black/55 text-white/85"
          }`}
        >
          <ChevronsDown className="size-4" />
          Crouch
        </button>
      </div>

      <button
        type="button"
        onClick={() => store?.exit()}
        className="absolute right-6 top-4 flex items-center gap-2 rounded-full bg-black/60 px-4 py-2 text-sm text-white/80 backdrop-blur"
      >
        <LogOut className="size-4" />
        Exit
      </button>
    </div>
  )
}
