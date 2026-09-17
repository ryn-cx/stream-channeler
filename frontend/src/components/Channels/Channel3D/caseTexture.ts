// TODO: Validate
import * as THREE from "three"

export type StoreTitle = {
  id: string
  name: string
  year: number | null
  imageUrl: string | null
  isPoster: boolean
  fullImageUrl: string | null
  backImageUrl: string | null
  description: string | null
  genres: string[]
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
export const genreHue = (genre: string) => hashHue(genre)

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
const mirrorColumn = (
  context: CanvasRenderingContext2D,
  canvas: HTMLCanvasElement,
  sourceX: number,
  width: number,
  destinationX: number,
  scale: number,
) => {
  context.save()
  context.translate(destinationX + width, 0)
  context.scale(-1, 1)
  context.drawImage(
    canvas,
    sourceX * scale,
    0,
    width * scale,
    224 * scale,
    0,
    0,
    width,
    224,
  )
  context.restore()
}

// TODO: Validate
const mirrorRow = (
  context: CanvasRenderingContext2D,
  canvas: HTMLCanvasElement,
  sourceY: number,
  height: number,
  destinationY: number,
  scale: number,
) => {
  context.save()
  context.translate(0, destinationY + height)
  context.scale(1, -1)
  context.drawImage(
    canvas,
    0,
    sourceY * scale,
    168 * scale,
    height * scale,
    0,
    0,
    168,
    height,
  )
  context.restore()
}

// TODO: Validate
export const createCaseCanvas = (
  title: StoreTitle,
  image: HTMLImageElement | null,
  scale = 1,
) => {
  const canvas = document.createElement("canvas")
  canvas.width = 256 * scale
  canvas.height = 256 * scale
  const context = canvas.getContext("2d")
  if (!context) return canvas
  context.scale(scale, scale)
  const hue = hashHue(title.id)

  context.fillStyle = "#0a0a0c"
  context.fillRect(0, 0, 256, 256)

  const posterOnly = title.isPoster && Boolean(image?.naturalWidth)

  context.save()
  context.beginPath()
  context.rect(0, 0, 168, 224)
  context.clip()
  drawCover(context, image, hue)

  if (posterOnly) {
    context.restore()
  } else {
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
  }

  mirrorColumn(context, canvas, 0, 24, 168, scale)
  context.fillStyle = "rgba(0, 0, 0, 0.3)"
  context.fillRect(168, 0, 24, 224)
  context.save()
  context.translate(180, 112)
  context.rotate(-Math.PI / 2)
  context.textAlign = "center"
  context.font = "bold 13px 'Trebuchet MS', sans-serif"
  context.fillStyle = "#f2f2f5"
  context.shadowColor = "rgba(0, 0, 0, 0.95)"
  context.shadowBlur = 5
  const spineLines = wrapLines(context, title.name, 196, 1)
  context.fillText(spineLines[0] ?? "", 0, 5)
  context.shadowBlur = 0
  context.restore()

  mirrorColumn(context, canvas, 144, 24, 192, scale)
  context.fillStyle = "rgba(0, 0, 0, 0.3)"
  context.fillRect(192, 0, 24, 224)

  mirrorColumn(context, canvas, 128, 40, 216, scale)
  context.fillStyle = "rgba(0, 0, 0, 0.55)"
  context.fillRect(216, 0, 40, 224)

  mirrorRow(context, canvas, 0, 16, 224, scale)
  context.fillStyle = "rgba(0, 0, 0, 0.3)"
  context.fillRect(0, 224, 168, 16)

  mirrorRow(context, canvas, 208, 16, 240, scale)
  context.fillStyle = "rgba(0, 0, 0, 0.3)"
  context.fillRect(0, 240, 168, 16)

  return canvas
}

// TODO: Validate
export const createBackCanvas = (
  title: StoreTitle,
  image: HTMLImageElement | null,
  cover: HTMLImageElement | null,
) => {
  const canvas = document.createElement("canvas")
  canvas.width = 672
  canvas.height = 896
  const context = canvas.getContext("2d")
  if (!context) return canvas
  const hue = hashHue(title.id)

  if (cover?.naturalWidth && cover.naturalHeight) {
    const scale = Math.max(672 / cover.naturalWidth, 896 / cover.naturalHeight)
    const width = cover.naturalWidth * scale
    const height = cover.naturalHeight * scale
    context.drawImage(
      cover,
      (672 - width) / 2,
      (896 - height) / 2,
      width,
      height,
    )
    context.fillStyle = "rgba(6, 6, 10, 0.86)"
    context.fillRect(0, 0, 672, 896)
  } else {
    const backdrop = context.createLinearGradient(0, 0, 0, 896)
    backdrop.addColorStop(0, `hsl(${hue}, 32%, 16%)`)
    backdrop.addColorStop(1, "#0b0b10")
    context.fillStyle = backdrop
    context.fillRect(0, 0, 672, 896)
  }

  context.save()
  context.beginPath()
  context.rect(36, 36, 600, 338)
  context.clip()
  if (image?.naturalWidth && image.naturalHeight) {
    const scale = Math.max(600 / image.naturalWidth, 338 / image.naturalHeight)
    const width = image.naturalWidth * scale
    const height = image.naturalHeight * scale
    context.drawImage(
      image,
      36 + (600 - width) / 2,
      36 + (338 - height) / 2,
      width,
      height,
    )
  } else {
    context.fillStyle = `hsl(${hue}, 40%, 24%)`
    context.fillRect(36, 36, 600, 338)
  }
  context.restore()
  context.strokeStyle = "rgba(255, 255, 255, 0.18)"
  context.lineWidth = 2
  context.strokeRect(36, 36, 600, 338)

  context.textAlign = "left"
  context.textBaseline = "alphabetic"
  context.fillStyle = "#f4f4f5"
  context.font = "bold 44px 'Trebuchet MS', sans-serif"
  const nameLines = wrapLines(context, title.name, 600, 2)
  let textY = 448
  for (const line of nameLines) {
    context.fillText(line, 36, textY)
    textY += 50
  }

  context.font = "24px 'Trebuchet MS', sans-serif"
  context.fillStyle = `hsl(${hue}, 58%, 68%)`
  const episodes =
    title.episodeCount === 1 ? "1 episode" : `${title.episodeCount} episodes`
  const seasons =
    title.seasonCount === 1 ? "1 season" : `${title.seasonCount} seasons`
  const facts = [
    title.year ? `${title.year}` : null,
    title.seasonCount > 0 ? seasons : null,
    episodes,
  ].filter(Boolean)
  context.fillText(facts.join("  \u00b7  "), 36, textY + 8)
  textY += 52

  if (title.genres.length > 0) {
    context.font = "22px 'Trebuchet MS', sans-serif"
    context.fillStyle = "rgba(235, 235, 240, 0.7)"
    for (const line of wrapLines(context, title.genres.join(" / "), 600, 2)) {
      context.fillText(line, 36, textY + 8)
      textY += 30
    }
  }

  if (title.description) {
    context.font = "23px 'Trebuchet MS', sans-serif"
    context.fillStyle = "rgba(226, 226, 233, 0.82)"
    textY += 26
    for (const line of wrapLines(context, title.description, 600, 12)) {
      context.fillText(line, 36, textY)
      textY += 32
    }
  }

  context.fillStyle = "rgba(255, 255, 255, 0.10)"
  context.fillRect(36, 830, 600, 30)
  return canvas
}

// TODO: Validate
export const createBackTexture = (
  title: StoreTitle,
  image: HTMLImageElement | null,
  cover: HTMLImageElement | null,
) => {
  const texture = new THREE.CanvasTexture(createBackCanvas(title, image, cover))
  texture.colorSpace = THREE.SRGBColorSpace
  texture.anisotropy = 4
  return texture
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
export const createBannerTexture = (genre: string) => {
  const canvas = document.createElement("canvas")
  canvas.width = 1536
  canvas.height = 128
  const context = canvas.getContext("2d")
  if (context) {
    const hue = hashHue(genre)
    context.fillStyle = `hsl(${hue}, 38%, 13%)`
    context.fillRect(0, 0, 1536, 128)
    context.fillStyle = `hsl(${hue}, 62%, 52%)`
    context.fillRect(0, 0, 1536, 8)
    context.fillRect(0, 120, 1536, 8)
    context.textAlign = "center"
    context.textBaseline = "middle"
    context.fillStyle = "#f6f6f8"
    context.shadowColor = "rgba(0, 0, 0, 0.8)"
    context.shadowBlur = 8
    let fontSize = 78
    const label = genre.toUpperCase()
    context.font = `bold ${fontSize}px 'Trebuchet MS', sans-serif`
    while (context.measureText(label).width > 1380 && fontSize > 24) {
      fontSize -= 4
      context.font = `bold ${fontSize}px 'Trebuchet MS', sans-serif`
    }
    context.fillText(label, 768, 68)
  }
  const texture = new THREE.CanvasTexture(canvas)
  texture.colorSpace = THREE.SRGBColorSpace
  texture.anisotropy = 4
  return texture
}

// TODO: Validate
const drawSignHalf = (
  context: CanvasRenderingContext2D,
  genres: string[],
  x: number,
) => {
  if (genres.length === 0) {
    context.fillStyle = "rgba(255, 255, 255, 0.06)"
    context.fillRect(x + 24, 40, 440, 176)
    return
  }
  context.fillStyle = "rgba(255, 255, 255, 0.04)"
  context.fillRect(x + 24, 40, 440, 176)
  const height = Math.min(52, Math.floor(176 / genres.length))
  let top = 40 + (176 - height * genres.length) / 2
  for (const genre of genres) {
    const hue = hashHue(genre)
    context.fillStyle = `hsl(${hue}, 44%, 18%)`
    context.fillRect(x + 24, top + 2, 440, height - 4)
    context.fillStyle = `hsl(${hue}, 66%, 55%)`
    context.fillRect(x + 24, top + 2, 10, height - 4)
    context.textAlign = "left"
    context.textBaseline = "middle"
    context.fillStyle = "#f6f6f8"
    let fontSize = Math.min(44, height - 14)
    const label = genre.toUpperCase()
    context.font = `bold ${fontSize}px 'Trebuchet MS', sans-serif`
    while (context.measureText(label).width > 400 && fontSize > 14) {
      fontSize -= 2
      context.font = `bold ${fontSize}px 'Trebuchet MS', sans-serif`
    }
    context.fillText(label, x + 46, top + height / 2)
    top += height
  }
}

// TODO: Validate
export const createAisleSignCanvas = (left: string[], right: string[]) => {
  const canvas = document.createElement("canvas")
  canvas.width = 1024
  canvas.height = 256
  const context = canvas.getContext("2d")
  if (context) {
    context.fillStyle = "#0b0b10"
    context.fillRect(0, 0, 1024, 256)
    context.strokeStyle = "rgba(255, 255, 255, 0.16)"
    context.lineWidth = 6
    context.strokeRect(3, 3, 1018, 250)
    drawSignHalf(context, left, 0)
    drawSignHalf(context, right, 512)
    context.fillStyle = "rgba(255, 255, 255, 0.12)"
    context.fillRect(510, 40, 4, 176)
  }
  return canvas
}

// TODO: Validate
export const createAisleSignTexture = (left: string[], right: string[]) => {
  const texture = new THREE.CanvasTexture(createAisleSignCanvas(left, right))
  texture.colorSpace = THREE.SRGBColorSpace
  texture.anisotropy = 4
  return texture
}

// TODO: Validate
export const createTagTexture = (genre: string) => {
  const canvas = document.createElement("canvas")
  canvas.width = 512
  canvas.height = 128
  const context = canvas.getContext("2d")
  if (context) {
    const hue = hashHue(genre)
    context.fillStyle = `hsl(${hue}, 52%, 22%)`
    context.fillRect(0, 0, 512, 128)
    context.fillStyle = `hsl(${hue}, 70%, 58%)`
    context.fillRect(0, 0, 512, 12)
    context.textAlign = "center"
    context.textBaseline = "middle"
    context.fillStyle = "#f8f8fa"
    let fontSize = 72
    const label = genre.toUpperCase()
    context.font = `bold ${fontSize}px 'Trebuchet MS', sans-serif`
    while (context.measureText(label).width > 460 && fontSize > 18) {
      fontSize -= 3
      context.font = `bold ${fontSize}px 'Trebuchet MS', sans-serif`
    }
    context.fillText(label, 256, 74)
  }
  const texture = new THREE.CanvasTexture(canvas)
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
