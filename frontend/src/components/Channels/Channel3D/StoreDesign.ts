// TODO: Validate
export type StoreDesign = {
  floor: number
  room: number
  shine: boolean
  unlit: boolean
  format: number
  lights: number
  lamps: number
  fullPosters: boolean
  outdoor: number
  askew: number
  rainDrops: number
  rainSpeed: number
  fps: boolean
  autoplayTrailers: boolean
}

export const PALETTE = [
  { name: "Blue", color: 0x1f3a8a },
  { name: "Red", color: 0x8a1f2f },
  { name: "Green", color: 0x1f6b3a },
  { name: "Purple", color: 0x5b2f7a },
  { name: "Yellow", color: 0xd8b13a },
  { name: "Slate", color: 0x2b2f3a },
]

export const FORMATS = ["DVD", "VHS", "Large DVD"]

export const defaultDesign: StoreDesign = {
  floor: 0x1f3a8a,
  room: 0xd8b13a,
  shine: true,
  unlit: true,
  format: 0,
  lights: 2,
  lamps: 24,
  fullPosters: false,
  outdoor: 2,
  askew: 20,
  rainDrops: 12000,
  rainSpeed: 14,
  fps: false,
  autoplayTrailers: true,
}

// TODO: Validate
const colorName = (color: number) =>
  PALETTE.find((entry) => entry.color === color)?.name ?? "Custom"

// TODO: Validate
export const designSummary = (design: StoreDesign) => [
  `Cases: ${FORMATS[design.format] ?? FORMATS[0]}`,
  `Floor: ${colorName(design.floor)}`,
  `Walls: ${colorName(design.room)}`,
  `Indoor lights: ${design.lights.toFixed(1)}`,
  `Lit lamps: ${design.lamps}`,
  `Outdoor lights: ${design.outdoor.toFixed(1)}`,
  `Askew: ${design.askew}`,
  `Rain: ${design.rainDrops.toLocaleString()} drops`,
  `Posters: ${design.fullPosters ? "full size" : "thumbnail"}`,
  `Shine: ${design.shine ? "on" : "off"}`,
  `Unlit cases: ${design.unlit ? "on" : "off"}`,
]
