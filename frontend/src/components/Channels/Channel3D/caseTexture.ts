// TODO: Validate
import * as THREE from "three"

export type StoreTitle = {
  id: string
  name: string
  year: number | null
  imageUrl: string | null
  episodeCount: number
  seasonCount: number
  url: string | null
}

// TODO: Validate
const hashHue = (value: string) => {
  let hash = 0
  for (let index = 0; index < value.length; index++) {
    hash = (hash * 31 + value.charCodeAt(index)) % 360
  }
  return hash
}

// TODO: Validate
const wrapLines = (
  context: CanvasRenderingContext2D,
  text: string,
  maxWidth: number,
  maxLines: number,
) => {
  const words = text.split(/\s+/).filter(Boolean)
  const lines: string[] = []
  let current = ""
  for (const word of words) {
    const candidate = current ? `${current} ${word}` : word
    if (!current || context.measureText(candidate).width <= maxWidth) {
      current = candidate
      continue
    }
    lines.push(current)
    current = word
    if (lines.length === maxLines) break
  }
  if (lines.length < maxLines && current) lines.push(current)
  const overflowed =
    lines.length === maxLines && current !== lines[maxLines - 1]
  if (overflowed) {
    let last = lines[maxLines - 1]
    while (
      last.length > 1 &&
      context.measureText(`${last}…`).width > maxWidth
    ) {
      last = last.slice(0, -1)
    }
    lines[maxLines - 1] = `${last}…`
  }
  return lines
}

// TODO: Validate
const drawCover = (
  context: CanvasRenderingContext2D,
  image: HTMLImageElement | null,
  hue: number,
) => {
  if (!image?.naturalWidth || !image.naturalHeight) {
    const gradient = context.createLinearGradient(0, 0, 168, 224)
    gradient.addColorStop(0, `hsl(${hue}, 48%, 34%)`)
    gradient.addColorStop(1, `hsl(${(hue + 40) % 360}, 52%, 12%)`)
    context.fillStyle = gradient
    context.fillRect(0, 0, 168, 224)
    return
  }
  const scale = Math.max(168 / image.naturalWidth, 224 / image.naturalHeight)
  const width = image.naturalWidth * scale
  const height = image.naturalHeight * scale
  context.drawImage(image, (168 - width) / 2, (224 - height) / 2, width, height)
}

// TODO: Validate
export const createCaseCanvas = (
  title: StoreTitle,
  image: HTMLImageElement | null,
) => {
  const canvas = document.createElement("canvas")
  canvas.width = 256
  canvas.height = 256
  const context = canvas.getContext("2d")
  if (!context) return canvas
  const hue = hashHue(title.id)

  context.fillStyle = "#0a0a0c"
  context.fillRect(0, 0, 256, 256)

  context.save()
  context.beginPath()
  context.rect(0, 0, 168, 224)
  context.clip()
  drawCover(context, image, hue)

  const shade = context.createLinearGradient(0, 96, 0, 224)
  shade.addColorStop(0, "rgba(0, 0, 0, 0)")
  shade.addColorStop(0.55, "rgba(0, 0, 0, 0.72)")
  shade.addColorStop(1, "rgba(0, 0, 0, 0.95)")
  context.fillStyle = shade
  context.fillRect(0, 96, 168, 128)
  context.restore()

  context.textAlign = "center"
  context.font = "bold 17px 'Trebuchet MS', sans-serif"
  const lines = wrapLines(context, title.name, 148, 3)
  let textY = 206 - (lines.length - 1) * 19
  context.fillStyle = "#f4f4f5"
  context.shadowColor = "rgba(0, 0, 0, 0.9)"
  context.shadowBlur = 4
  for (const line of lines) {
    context.fillText(line, 84, textY)
    textY += 19
  }
  context.shadowBlur = 0

  context.font = "10px 'Trebuchet MS', sans-serif"
  context.fillStyle = "rgba(230, 230, 235, 0.65)"
  const episodes =
    title.episodeCount === 1 ? "1 EPISODE" : `${title.episodeCount} EPISODES`
  context.fillText(
    title.year ? `${title.year} · ${episodes}` : episodes,
    84,
    219,
  )

  context.strokeStyle = "rgba(0, 0, 0, 0.85)"
  context.lineWidth = 7
  context.strokeRect(3.5, 3.5, 161, 217)
  context.strokeStyle = "rgba(255, 255, 255, 0.14)"
  context.lineWidth = 1
  context.strokeRect(7.5, 7.5, 153, 209)

  context.fillStyle = `hsl(${hue}, 42%, 26%)`
  context.fillRect(168, 0, 24, 224)
  context.fillStyle = "rgba(255, 255, 255, 0.10)"
  context.fillRect(168, 0, 3, 224)
  context.save()
  context.translate(180, 112)
  context.rotate(-Math.PI / 2)
  context.textAlign = "center"
  context.font = "bold 13px 'Trebuchet MS', sans-serif"
  context.fillStyle = "#eaeaee"
  const spineLines = wrapLines(context, title.name, 196, 1)
  context.fillText(spineLines[0] ?? "", 0, 5)
  context.restore()

  context.fillStyle = "#131316"
  context.fillRect(192, 0, 64, 224)
  context.fillStyle = "#1d1d21"
  context.fillRect(192, 0, 10, 224)

  return canvas
}

// TODO: Validate
export const createCaseTexture = (
  title: StoreTitle,
  image: HTMLImageElement | null,
) => {
  const texture = new THREE.CanvasTexture(createCaseCanvas(title, image))
  texture.colorSpace = THREE.SRGBColorSpace
  texture.anisotropy = 4
  return texture
}

// TODO: Validate
export const createSignTexture = (text: string) => {
  const canvas = document.createElement("canvas")
  canvas.width = 1024
  canvas.height = 256
  const context = canvas.getContext("2d")
  if (context) {
    context.fillStyle = "#0d1220"
    context.fillRect(0, 0, 1024, 256)
    context.strokeStyle = "#2dd4bf"
    context.lineWidth = 8
    context.strokeRect(14, 14, 996, 228)
    context.textAlign = "center"
    context.textBaseline = "middle"
    context.fillStyle = "#e9fdf9"
    context.shadowColor = "#2dd4bf"
    context.shadowBlur = 26
    let fontSize = 104
    context.font = `bold ${fontSize}px 'Trebuchet MS', sans-serif`
    while (context.measureText(text).width > 920 && fontSize > 30) {
      fontSize -= 4
      context.font = `bold ${fontSize}px 'Trebuchet MS', sans-serif`
    }
    context.fillText(text, 512, 132)
  }
  const texture = new THREE.CanvasTexture(canvas)
  texture.colorSpace = THREE.SRGBColorSpace
  return texture
}

// TODO: Validate
export const createCarpetTexture = () => {
  const canvas = document.createElement("canvas")
  canvas.width = 128
  canvas.height = 128
  const context = canvas.getContext("2d")
  if (context) {
    context.fillStyle = "#2b1f2e"
    context.fillRect(0, 0, 128, 128)
    for (let index = 0; index < 2600; index++) {
      const lightness = 14 + Math.random() * 22
      context.fillStyle = `hsl(${292 + Math.random() * 24}, ${18 + Math.random() * 26}%, ${lightness}%)`
      context.fillRect(Math.random() * 128, Math.random() * 128, 2, 2)
    }
  }
  const texture = new THREE.CanvasTexture(canvas)
  texture.colorSpace = THREE.SRGBColorSpace
  texture.wrapS = THREE.RepeatWrapping
  texture.wrapT = THREE.RepeatWrapping
  texture.repeat.set(30, 30)
  return texture
}
