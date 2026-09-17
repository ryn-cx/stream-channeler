// TODO: Validate
export type StoreDesign = {
  floor: number
  room: number
  shine: boolean
  format: number
  lights: number
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

export const LIGHT_LEVELS = ["Low", "Normal", "Bright", "Max"]

export const defaultDesign: StoreDesign = {
  floor: 0x1f3a8a,
  room: 0xd8b13a,
  shine: true,
  format: 0,
  lights: 1,
}

// TODO: Validate
const colorName = (color: number) =>
  PALETTE.find((entry) => entry.color === color)?.name ?? "Custom"

// TODO: Validate
export const designSummary = (design: StoreDesign) => [
  `Cases: ${FORMATS[design.format] ?? FORMATS[0]}`,
  `Floor: ${colorName(design.floor)}`,
  `Walls: ${colorName(design.room)}`,
  `Lights: ${LIGHT_LEVELS[design.lights] ?? LIGHT_LEVELS[1]}`,
  `Shine: ${design.shine ? "on" : "off"}`,
]
