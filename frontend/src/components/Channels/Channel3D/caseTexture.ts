// TODO: Validate
import * as THREE from "three"

export type StoreGenre = {
  source: string
  name: string
}

// TODO: Validate
export type StoreTitle = {
  id: string
  name: string
  year: number | null
  score: number | null
  popularity: number | null
  mediaType: string | null
  originalLanguage: string | null
  languages: string[]
  imageUrl: string | null
  isPoster: boolean
  genres: StoreGenre[]
  episodeCount: number
  seasonCount: number
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
export const shelfGenres = (title: StoreTitle) =>
  [...new Set(title.genres.map((genre) => genre.name))].sort((left, right) =>
    left.localeCompare(right),
  )

// TODO: Validate
export const isMovie = (title: StoreTitle) => title.mediaType === "Movie"

// TODO: Validate
export const titleFacts = (title: StoreTitle) => {
  if (isMovie(title)) return ["Movie"]
  const seasons =
    title.seasonCount === 1 ? "1 season" : `${title.seasonCount} seasons`
  const episodes =
    title.episodeCount === 1 ? "1 episode" : `${title.episodeCount} episodes`
  return title.seasonCount > 0 ? [seasons, episodes] : [episodes]
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
  context.drawImage(image, 0, 0, 168, 224)
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
  context.filter = "blur(7px)"
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
    const summary = isMovie(title)
      ? "MOVIE"
      : title.episodeCount === 1
        ? "1 EPISODE"
        : `${title.episodeCount} EPISODES`
    context.fillText(
      title.year ? `${title.year} · ${summary}` : summary,
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

  context.fillStyle = "#33333a"
  context.fillRect(192, 0, 24, 224)

  context.fillStyle = "#26262b"
  context.fillRect(216, 0, 40, 224)

  context.fillStyle = "#3a3a42"
  context.fillRect(0, 224, 168, 16)

  context.fillStyle = "#2c2c33"
  context.fillRect(0, 240, 168, 16)

  return canvas
}

// TODO: Validate
export type CaseDetail = {
  description: string | null
  originalLanguage: string | null
  languages: string[]
}

// TODO: Validate
export const createBackCanvas = (
  title: StoreTitle,
  detail: CaseDetail,
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
  const facts = [
    title.year ? `${title.year}` : null,
    ...titleFacts(title),
    title.score === null ? null : `Score ${title.score.toFixed(1)}`,
  ].filter(Boolean)
  context.fillText(facts.join("  \u00b7  "), 36, textY + 8)
  textY += 52

  const shelved = shelfGenres(title)
  if (shelved.length > 0) {
    context.font = "22px 'Trebuchet MS', sans-serif"
    context.fillStyle = "rgba(235, 235, 240, 0.7)"
    for (const line of wrapLines(context, shelved.join(" / "), 600, 2)) {
      context.fillText(line, 36, textY + 8)
      textY += 30
    }
  }

  const spoken = detail.languages.filter(
    (language) => language !== detail.originalLanguage,
  )
  if (detail.originalLanguage || spoken.length > 0) {
    context.fillStyle = "rgba(235, 235, 240, 0.75)"
    let languageX = 36
    if (detail.originalLanguage) {
      context.font = "bold 22px 'Trebuchet MS', sans-serif"
      context.fillText(detail.originalLanguage, languageX, textY + 8)
      languageX += context.measureText(detail.originalLanguage).width
    }
    if (spoken.length > 0) {
      context.font = "22px 'Trebuchet MS', sans-serif"
      context.fillStyle = "rgba(235, 235, 240, 0.55)"
      const rest = detail.originalLanguage
        ? `, ${spoken.join(", ")}`
        : spoken.join(", ")
      context.fillText(
        wrapLines(context, rest, 636 - languageX, 1)[0] ?? "",
        languageX,
        textY + 8,
      )
    }
    textY += 32
  }

  if (detail.description) {
    context.font = "23px 'Trebuchet MS', sans-serif"
    context.fillStyle = "rgba(226, 226, 233, 0.82)"
    textY += 26
    for (const line of wrapLines(context, detail.description, 600, 12)) {
      context.fillText(line, 36, textY)
      textY += 32
    }
  }

  return canvas
}

// TODO: Validate
export const createBackTexture = (
  title: StoreTitle,
  detail: CaseDetail,
  image: HTMLImageElement | null,
  cover: HTMLImageElement | null,
) => {
  const texture = new THREE.CanvasTexture(
    createBackCanvas(title, detail, image, cover),
  )
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

  const columns = Math.ceil(genres.length / 6)
  const rows = Math.ceil(genres.length / columns)
  const columnWidth = 440 / columns
  const height = Math.min(52, Math.floor(176 / rows))
  const top = 40 + (176 - height * rows) / 2

  for (const [index, genre] of genres.entries()) {
    const column = Math.floor(index / rows)
    const left = x + 24 + column * columnWidth
    const rowTop = top + (index % rows) * height
    const hue = hashHue(genre)
    context.fillStyle = `hsl(${hue}, 44%, 18%)`
    context.fillRect(left + 2, rowTop + 2, columnWidth - 6, height - 4)
    context.fillStyle = `hsl(${hue}, 66%, 55%)`
    context.fillRect(left + 2, rowTop + 2, 8, height - 4)
    context.textAlign = "left"
    context.textBaseline = "middle"
    context.fillStyle = "#f6f6f8"
    let fontSize = Math.min(40, height - 12)
    const label = genre.toUpperCase()
    context.font = `bold ${fontSize}px 'Trebuchet MS', sans-serif`
    while (
      context.measureText(label).width > columnWidth - 28 &&
      fontSize > 12
    ) {
      fontSize -= 2
      context.font = `bold ${fontSize}px 'Trebuchet MS', sans-serif`
    }
    context.fillText(label, left + 18, rowTop + height / 2)
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
const drawBoardColumn = (
  context: CanvasRenderingContext2D,
  heading: string,
  lines: string[],
  x: number,
  width: number,
) => {
  context.textAlign = "left"
  context.textBaseline = "alphabetic"
  context.fillStyle = "#7de9dc"
  context.font = "bold 26px 'Trebuchet MS', sans-serif"
  context.fillText(heading, x, 40)
  context.fillStyle = "rgba(125, 233, 220, 0.3)"
  context.fillRect(x, 50, width, 3)

  let textY = 86
  for (const [index, line] of lines.entries()) {
    context.fillStyle = index === 0 ? "#f4f4f5" : "rgba(226, 226, 233, 0.78)"
    context.font =
      index === 0
        ? "bold 25px 'Trebuchet MS', sans-serif"
        : "22px 'Trebuchet MS', sans-serif"
    context.fillText(line, x, textY)
    textY += index === 0 ? 34 : 28
  }
}

// TODO: Validate
export const createFilterBoardTexture = (
  filters: string[],
  design: string[],
) => {
  const canvas = document.createElement("canvas")
  canvas.width = 1024
  canvas.height = 276
  const context = canvas.getContext("2d")
  if (context) {
    context.fillStyle = "#0b0d14"
    context.fillRect(0, 0, 1024, 276)
    context.strokeStyle = "rgba(45, 212, 191, 0.5)"
    context.lineWidth = 5
    context.strokeRect(3, 3, 1018, 270)

    drawBoardColumn(context, "NOW SHOWING", filters, 26, 590)
    context.fillStyle = "rgba(255, 255, 255, 0.12)"
    context.fillRect(652, 26, 3, 224)
    drawBoardColumn(context, "STYLE", design, 684, 314)
  }
  const texture = new THREE.CanvasTexture(canvas)
  texture.colorSpace = THREE.SRGBColorSpace
  texture.anisotropy = 4
  return texture
}

// TODO: Validate
export const createStoreSignTexture = (name: string) => {
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
    const label = name.toUpperCase()
    context.font = `bold ${fontSize}px 'Trebuchet MS', sans-serif`
    while (context.measureText(label).width > 900 && fontSize > 28) {
      fontSize -= 4
      context.font = `bold ${fontSize}px 'Trebuchet MS', sans-serif`
    }
    context.fillText(label, 512, 132)
  }
  const texture = new THREE.CanvasTexture(canvas)
  texture.colorSpace = THREE.SRGBColorSpace
  texture.anisotropy = 4
  return texture
}

// TODO: Validate
export const createLoaderTexture = () => {
  const canvas = document.createElement("canvas")
  canvas.width = 512
  canvas.height = 160
  const context = canvas.getContext("2d")
  if (context) {
    context.fillStyle = "#0d1220"
    context.fillRect(0, 0, 512, 160)
    context.strokeStyle = "#2dd4bf"
    context.lineWidth = 6
    context.strokeRect(3, 3, 506, 154)
    context.textAlign = "center"
    context.textBaseline = "middle"
    context.fillStyle = "#e9fdf9"
    context.shadowColor = "#2dd4bf"
    context.shadowBlur = 18
    context.font = "bold 54px 'Trebuchet MS', sans-serif"
    context.fillText("LOAD COVERS", 256, 66)
    context.shadowBlur = 0
    context.font = "26px 'Trebuchet MS', sans-serif"
    context.fillStyle = "rgba(233, 253, 249, 0.62)"
    context.fillText("this side of the aisle", 256, 116)
  }
  const texture = new THREE.CanvasTexture(canvas)
  texture.colorSpace = THREE.SRGBColorSpace
  texture.anisotropy = 4
  return texture
}

// TODO: Validate
export const createLabelTexture = (label: string) => {
  const canvas = document.createElement("canvas")
  canvas.width = 512
  canvas.height = 128
  const context = canvas.getContext("2d")
  if (context) {
    context.fillStyle = "rgba(10, 10, 14, 0.85)"
    context.fillRect(0, 0, 512, 128)
    context.textAlign = "center"
    context.textBaseline = "middle"
    context.fillStyle = "#f4f4f5"
    context.font = "bold 58px 'Trebuchet MS', sans-serif"
    context.fillText(label.toUpperCase(), 256, 68)
  }
  const texture = new THREE.CanvasTexture(canvas)
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
export const createDiffuserTexture = () => {
  const canvas = document.createElement("canvas")
  canvas.width = 64
  canvas.height = 256
  const context = canvas.getContext("2d")
  if (context) {
    context.fillStyle = "#efe7d2"
    context.fillRect(0, 0, 64, 256)

    for (const center of [20, 44]) {
      const tube = context.createLinearGradient(center - 12, 0, center + 12, 0)
      tube.addColorStop(0, "rgba(255, 249, 232, 0)")
      tube.addColorStop(0.5, "rgba(255, 253, 244, 0.95)")
      tube.addColorStop(1, "rgba(255, 249, 232, 0)")
      context.fillStyle = tube
      context.fillRect(center - 12, 6, 24, 244)
    }

    const ends = context.createLinearGradient(0, 0, 0, 256)
    ends.addColorStop(0, "rgba(64, 62, 54, 0.85)")
    ends.addColorStop(0.08, "rgba(120, 116, 104, 0)")
    ends.addColorStop(0.92, "rgba(120, 116, 104, 0)")
    ends.addColorStop(1, "rgba(64, 62, 54, 0.85)")
    context.fillStyle = ends
    context.fillRect(0, 0, 64, 256)

    context.strokeStyle = "rgba(90, 88, 80, 0.25)"
    context.lineWidth = 1
    for (let line = 8; line < 256; line += 16) {
      context.beginPath()
      context.moveTo(0, line)
      context.lineTo(64, line)
      context.stroke()
    }
  }
  const texture = new THREE.CanvasTexture(canvas)
  texture.colorSpace = THREE.SRGBColorSpace
  return texture
}

// TODO: Validate
export const createGlowTexture = () => {
  const canvas = document.createElement("canvas")
  canvas.width = 128
  canvas.height = 128
  const context = canvas.getContext("2d")
  if (context) {
    const glow = context.createRadialGradient(64, 64, 4, 64, 64, 64)
    glow.addColorStop(0, "rgba(255, 244, 222, 0.22)")
    glow.addColorStop(0.5, "rgba(255, 238, 205, 0.09)")
    glow.addColorStop(1, "rgba(255, 236, 200, 0)")
    context.fillStyle = glow
    context.fillRect(0, 0, 128, 128)
  }
  const texture = new THREE.CanvasTexture(canvas)
  texture.colorSpace = THREE.SRGBColorSpace
  return texture
}

// TODO: Validate
export const createCeilingTexture = () => {
  const canvas = document.createElement("canvas")
  canvas.width = 128
  canvas.height = 256
  const context = canvas.getContext("2d")
  if (context) {
    context.fillStyle = "#e8e4d8"
    context.fillRect(0, 0, 128, 256)
    context.fillStyle = "rgba(122, 118, 106, 0.16)"
    for (let speck = 0; speck < 2800; speck++) {
      context.fillRect(Math.random() * 128, Math.random() * 256, 1, 1)
    }
    context.strokeStyle = "#b9b5a6"
    context.lineWidth = 6
    context.strokeRect(3, 3, 122, 250)
    context.strokeStyle = "rgba(255, 255, 255, 0.5)"
    context.lineWidth = 1.5
    context.strokeRect(6.5, 6.5, 115, 243)
  }
  const texture = new THREE.CanvasTexture(canvas)
  texture.colorSpace = THREE.SRGBColorSpace
  texture.wrapS = THREE.RepeatWrapping
  texture.wrapT = THREE.RepeatWrapping
  texture.anisotropy = 4
  return texture
}

// TODO: Validate
export const createLotTexture = (horizontal: boolean) => {
  const canvas = document.createElement("canvas")
  canvas.width = 128
  canvas.height = 128
  const context = canvas.getContext("2d")
  if (context) {
    context.fillStyle = "#17171c"
    context.fillRect(0, 0, 128, 128)
    context.fillStyle = "rgba(255, 255, 255, 0.05)"
    for (let speck = 0; speck < 900; speck++) {
      context.fillRect(Math.random() * 128, Math.random() * 128, 1, 1)
    }
    context.fillStyle = "#cdc7a6"
    if (horizontal) context.fillRect(0, 0, 128, 5)
    else context.fillRect(0, 0, 5, 128)
  }
  const texture = new THREE.CanvasTexture(canvas)
  texture.colorSpace = THREE.SRGBColorSpace
  texture.wrapS = THREE.RepeatWrapping
  texture.wrapT = THREE.RepeatWrapping
  texture.anisotropy = 4
  return texture
}

// TODO: Validate
export const createGrassTexture = () => {
  const canvas = document.createElement("canvas")
  canvas.width = 128
  canvas.height = 128
  const context = canvas.getContext("2d")
  if (context) {
    context.fillStyle = "#1c2a1c"
    context.fillRect(0, 0, 128, 128)
    for (let blade = 0; blade < 2600; blade++) {
      const shade = 18 + Math.floor(Math.random() * 26)
      context.fillStyle = `rgb(${shade}, ${shade + 16}, ${shade})`
      context.fillRect(Math.random() * 128, Math.random() * 128, 1, 2)
    }
  }
  const texture = new THREE.CanvasTexture(canvas)
  texture.colorSpace = THREE.SRGBColorSpace
  texture.wrapS = THREE.RepeatWrapping
  texture.wrapT = THREE.RepeatWrapping
  texture.anisotropy = 4
  return texture
}

// TODO: Validate
export const createRippleTexture = () => {
  const canvas = document.createElement("canvas")
  canvas.width = 64
  canvas.height = 64
  const context = canvas.getContext("2d")
  if (context) {
    const ring = context.createRadialGradient(32, 32, 16, 32, 32, 32)
    ring.addColorStop(0, "rgba(198, 222, 255, 0)")
    ring.addColorStop(0.72, "rgba(214, 234, 255, 0.55)")
    ring.addColorStop(0.9, "rgba(226, 240, 255, 0.22)")
    ring.addColorStop(1, "rgba(198, 222, 255, 0)")
    context.fillStyle = ring
    context.fillRect(0, 0, 64, 64)
  }
  const texture = new THREE.CanvasTexture(canvas)
  texture.colorSpace = THREE.SRGBColorSpace
  return texture
}

// TODO: Validate
export const createCarpetTexture = (hue = 214) => {
  const canvas = document.createElement("canvas")
  canvas.width = 256
  canvas.height = 256
  const context = canvas.getContext("2d")
  if (context) {
    context.fillStyle = `hsl(${hue}, 88%, 25%)`
    context.fillRect(0, 0, 256, 256)

    const weave = context.getImageData(0, 0, 256, 256)
    const pixels = weave.data
    for (let row = 0; row < 256; row++) {
      for (let column = 0; column < 256; column++) {
        const index = (row * 256 + column) * 4
        const tuft = ((row >> 1) + (column >> 1)) % 2 === 0 ? 1.06 : 0.94
        const fibre = tuft * (0.86 + Math.random() * 0.28)
        pixels[index] *= fibre
        pixels[index + 1] *= fibre
        pixels[index + 2] *= fibre
      }
    }
    context.putImageData(weave, 0, 0)
  }
  const texture = new THREE.CanvasTexture(canvas)
  texture.colorSpace = THREE.SRGBColorSpace
  texture.wrapS = THREE.RepeatWrapping
  texture.wrapT = THREE.RepeatWrapping
  texture.anisotropy = 16
  return texture
}
