// TODO: Validate
import { ChevronsDown, LogOut, Play } from "lucide-react"
import { useRef, useState } from "react"
import type { StoreTitle } from "./caseTexture"
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
export function TouchControls({
  store,
  focused,
}: {
  store: VideoStore | null
  focused: StoreTitle | null
}) {
  const [stick, setStick] = useState<{
    originX: number
    originY: number
    x: number
    y: number
  } | null>(null)
  const [crouching, setCrouching] = useState(false)
  const stickTouch = useRef<{ id: number; x: number; y: number } | null>(null)
  const lookTouch = useRef<{
    id: number
    x: number
    y: number
    travel: number
    at: number
  } | null>(null)

  // TODO: Validate
  const onStickStart = (event: React.TouchEvent) => {
    const touch = event.changedTouches[0]
    stickTouch.current = {
      id: touch.identifier,
      x: touch.clientX,
      y: touch.clientY,
    }
    setStick({ originX: touch.clientX, originY: touch.clientY, x: 0, y: 0 })
  }

  // TODO: Validate
  const onStickMove = (event: React.TouchEvent) => {
    const origin = stickTouch.current
    if (!origin) return
    const touch = findTouch(event.changedTouches, origin.id)
    if (!touch) return
    const deltaX = touch.clientX - origin.x
    const deltaY = touch.clientY - origin.y
    const distance = Math.hypot(deltaX, deltaY)
    const scale = distance > STICK_RADIUS ? STICK_RADIUS / distance : 1
    const knobX = deltaX * scale
    const knobY = deltaY * scale
    setStick({ originX: origin.x, originY: origin.y, x: knobX, y: knobY })
    store?.setMove(
      knobX / STICK_RADIUS,
      -knobY / STICK_RADIUS,
      distance > STICK_RADIUS * 0.85,
    )
  }

  // TODO: Validate
  const onStickEnd = () => {
    stickTouch.current = null
    setStick(null)
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
        className="absolute inset-y-0 right-0 w-1/2"
        onTouchStart={onLookStart}
        onTouchMove={onLookMove}
        onTouchEnd={onLookEnd}
        onTouchCancel={onLookEnd}
      />
      <div
        className="absolute inset-y-0 left-0 w-1/2"
        onTouchStart={onStickStart}
        onTouchMove={onStickMove}
        onTouchEnd={onStickEnd}
        onTouchCancel={onStickEnd}
      />

      {stick && (
        <div
          className="pointer-events-none absolute size-32 -translate-x-1/2 -translate-y-1/2 rounded-full border border-white/20 bg-white/5"
          style={{ left: stick.originX, top: stick.originY }}
        >
          <div
            className="absolute left-1/2 top-1/2 size-14 rounded-full border border-white/40 bg-white/30"
            style={{
              transform: `translate(calc(-50% + ${stick.x * 0.55}px), calc(-50% + ${stick.y * 0.55}px))`,
            }}
          />
        </div>
      )}

      <div className="absolute bottom-8 right-6 flex flex-col items-end gap-3">
        {focused?.url && (
          <button
            type="button"
            onClick={() => store?.activateFocused()}
            className="flex items-center gap-2 rounded-full bg-emerald-500/90 px-5 py-3 text-sm font-semibold text-black"
          >
            <Play className="size-4" />
            Open
          </button>
        )}
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
