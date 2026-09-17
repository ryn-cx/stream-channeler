// TODO: Validate
import * as THREE from "three"
import { PointerLockControls } from "three/examples/jsm/controls/PointerLockControls.js"
import {
  createAisleSignTexture,
  createBannerTexture,
  createCarpetTexture,
  createCaseTexture,
  createSignTexture,
  createTagTexture,
  genreHue,
  type StoreTitle,
} from "./caseTexture"

type Slot = { position: THREE.Vector3; facing: THREE.Vector3 }

type ShelfRun = {
  levels: Slot[][]
  order: Slot[]
  boards: THREE.Mesh[]
  aisle: number | null
  side: "left" | "right"
  wallBanner: { position: THREE.Vector3; facing: THREE.Vector3 } | null
}

type AisleSign = {
  left: string[]
  right: string[]
  near: THREE.Mesh
  far: THREE.Mesh
}

// TODO: Validate
export const isTouchDevice = () =>
  window.matchMedia("(pointer: coarse)").matches

export type VideoStoreCallbacks = {
  onFocus: (title: StoreTitle | null) => void
  onActivate: (title: StoreTitle) => void
  onLockChange: (locked: boolean) => void
}

// TODO: Validate
const buildCaseGeometry = () => {
  const geometry = new THREE.BoxGeometry(0.135, 0.19, 0.015)
  const leftEdge = { x: 168 / 256, y: 0.125, w: 24 / 256, h: 224 / 256 }
  const rightEdge = { x: 192 / 256, y: 0.125, w: 24 / 256, h: 224 / 256 }
  const back = { x: 216 / 256, y: 0.125, w: 40 / 256, h: 224 / 256 }
  const top = { x: 0, y: 16 / 256, w: 168 / 256, h: 16 / 256 }
  const bottom = { x: 0, y: 0, w: 168 / 256, h: 16 / 256 }
  const front = { x: 0, y: 0.125, w: 168 / 256, h: 224 / 256 }
  const rects = [rightEdge, leftEdge, top, bottom, front, back]
  const uv = geometry.attributes.uv
  for (let face = 0; face < 6; face++) {
    const rect = rects[face]
    for (let corner = 0; corner < 4; corner++) {
      const index = face * 4 + corner
      uv.setXY(
        index,
        rect.x + uv.getX(index) * rect.w,
        rect.y + uv.getY(index) * rect.h,
      )
    }
  }
  uv.needsUpdate = true
  return geometry
}

// TODO: Validate
const buildRunOrder = (rows: Slot[][]) => {
  const order: Slot[] = []
  for (let column = rows[0].length - 1; column >= 0; column--) {
    for (let row = rows.length - 1; row >= 0; row--) {
      order.push(rows[row][column])
    }
  }
  return order
}

// TODO: Validate
export class VideoStore {
  private container: HTMLElement
  private callbacks: VideoStoreCallbacks
  private renderer: THREE.WebGLRenderer
  private scene = new THREE.Scene()
  private camera: THREE.PerspectiveCamera
  private controls: PointerLockControls
  private clock = new THREE.Clock()
  private raycaster = new THREE.Raycaster()
  private pressed = new Set<string>()
  private colliders: THREE.Box3[] = []
  private caseMeshes: THREE.Mesh[] = []
  private focused: THREE.Mesh | null = null
  private velocity = new THREE.Vector3()
  private eyeHeight = 1.65
  private limit = new THREE.Vector2()
  private animationHandle = 0
  private disposed = false
  private pendingImages: Array<{ mesh: THREE.Mesh; run: () => void }> = []
  private activeImages = 0
  private runs: ShelfRun[] = []
  private aisleSigns: AisleSign[] = []
  private packOrder: number[] = []
  private aisleStarts: number[] = []
  private wallRun: ShelfRun | null = null
  private wallCases: THREE.Mesh[] = []
  private realCases: THREE.Mesh[] = []
  private genreCases = new Map<string, THREE.Mesh[]>()
  private tagPool: THREE.Mesh[] = []
  private tagGeometry = new THREE.PlaneGeometry(0.155, 0.042)
  private stripMaterials = new Map<string, THREE.MeshStandardMaterial>()
  private stripPool: THREE.Mesh[] = []
  private stripGeometry = new THREE.BoxGeometry(0.014, 0.018, 1)
  private placedTitles = 0
  private touchMove = new THREE.Vector2()
  private touchRun = false
  private touchCrouch = false
  private touchActive = false
  private lastExit = 0
  private euler = new THREE.Euler(0, 0, 0, "YXZ")
  readonly touch = isTouchDevice()
  private caseGeometry = buildCaseGeometry()
  private resizeObserver: ResizeObserver

  // TODO: Validate
  constructor(
    container: HTMLElement,
    slotCount: number,
    storeName: string,
    callbacks: VideoStoreCallbacks,
  ) {
    this.container = container
    this.callbacks = callbacks

    this.renderer = new THREE.WebGLRenderer({ antialias: true })
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
    this.renderer.setSize(container.clientWidth, container.clientHeight)
    container.appendChild(this.renderer.domElement)

    this.scene.background = new THREE.Color(0x07070b)
    this.scene.fog = new THREE.Fog(0x07070b, 12, 36)

    this.camera = new THREE.PerspectiveCamera(
      72,
      container.clientWidth / container.clientHeight,
      0.05,
      120,
    )
    this.controls = new PointerLockControls(this.camera, container)
    this.scene.add(this.camera)

    this.buildStore(slotCount, storeName)

    this.controls.addEventListener("lock", this.handleLock)
    this.controls.addEventListener("unlock", this.handleUnlock)
    window.addEventListener("keydown", this.handleKeyDown)
    window.addEventListener("keyup", this.handleKeyUp)
    window.addEventListener("mousedown", this.handleMouseDown)
    this.resizeObserver = new ResizeObserver(this.handleResize)
    this.resizeObserver.observe(container)

    this.animationHandle = requestAnimationFrame(this.tick)
  }

  // TODO: Validate
  private buildStore(slotCount: number, storeName: string) {
    const levels = [0.32, 0.68, 1.04, 1.4, 1.76]
    const slotWidth = 0.172
    const perLevel = 50
    const gondolaLength = perLevel * slotWidth
    const sides = Math.max(
      2,
      Math.ceil(slotCount / (levels.length * perLevel)) + 2,
    )
    const unitCount = Math.min(18, Math.max(1, Math.ceil(sides / 2)))
    const width = unitCount * 3.3 + 3.4
    const depth = gondolaLength + 6
    this.limit.set(width / 2 - 0.45, depth / 2 - 0.45)
    this.camera.position.set(width / 2 - 1.8, 1.65, depth / 2 - 2.35)
    this.camera.lookAt(width / 2 - 1.8, 1.35, depth / 2 - 1.3)

    const floor = new THREE.Mesh(
      new THREE.PlaneGeometry(width, depth),
      new THREE.MeshStandardMaterial({
        map: createCarpetTexture(),
        roughness: 0.95,
      }),
    )
    floor.rotation.x = -Math.PI / 2
    this.scene.add(floor)

    const ceiling = new THREE.Mesh(
      new THREE.PlaneGeometry(width, depth),
      new THREE.MeshStandardMaterial({ color: 0x15161c, roughness: 1 }),
    )
    ceiling.rotation.x = Math.PI / 2
    ceiling.position.y = 3.2
    this.scene.add(ceiling)

    const wallMaterial = new THREE.MeshStandardMaterial({
      color: 0x24262f,
      roughness: 0.9,
      side: THREE.DoubleSide,
    })
    const walls: Array<[number, number, number, number]> = [
      [0, -depth / 2, width, 0],
      [0, depth / 2, width, Math.PI],
      [-width / 2, 0, depth, Math.PI / 2],
      [width / 2, 0, depth, -Math.PI / 2],
    ]
    for (const [x, z, span, rotation] of walls) {
      const wall = new THREE.Mesh(
        new THREE.PlaneGeometry(span, 3.2),
        wallMaterial,
      )
      wall.position.set(x, 1.6, z)
      wall.rotation.y = rotation
      this.scene.add(wall)
    }

    const sign = new THREE.Mesh(
      new THREE.PlaneGeometry(4.4, 1.1),
      new THREE.MeshBasicMaterial({
        map: createSignTexture(storeName.toUpperCase()),
      }),
    )
    sign.position.set(0, 2.55, -depth / 2 + 0.08)
    this.scene.add(sign)

    this.scene.add(new THREE.AmbientLight(0xb8c4ff, 0.5))
    this.scene.add(new THREE.HemisphereLight(0xdfe6ff, 0x120c16, 0.8))

    const lightMaterial = new THREE.MeshBasicMaterial({ color: 0xfff6e2 })
    const lanes = unitCount + 1
    for (let lane = 0; lane < lanes; lane++) {
      const x = (lane - (lanes - 1) / 2) * 3.3
      const strip = new THREE.Mesh(
        new THREE.BoxGeometry(0.22, 0.06, gondolaLength * 0.9),
        lightMaterial,
      )
      strip.position.set(x, 3.12, -0.5)
      this.scene.add(strip)
      if (lane % Math.ceil(lanes / 8) === 0) {
        const lamp = new THREE.PointLight(0xfff1d8, 30, 18, 2)
        lamp.position.set(x, 2.95, -0.5)
        this.scene.add(lamp)
      }
    }
    const entranceLamp = new THREE.PointLight(0x9ad7ff, 20, 15, 2)
    entranceLamp.position.set(0, 2.9, depth / 2 - 1.6)
    this.scene.add(entranceLamp)

    const shelfMaterial = new THREE.MeshStandardMaterial({
      color: 0x6a4a33,
      roughness: 0.8,
    })
    const frameMaterial = new THREE.MeshStandardMaterial({
      color: 0x2e3038,
      roughness: 0.7,
      metalness: 0.35,
    })
    const runs: ShelfRun[] = []

    for (let unit = 0; unit < unitCount; unit++) {
      const x = (unit - (unitCount - 1) / 2) * 3.3
      const zStart = -0.5 - gondolaLength / 2

      const spine = new THREE.Mesh(
        new THREE.BoxGeometry(0.08, 2.05, gondolaLength),
        frameMaterial,
      )
      spine.position.set(x, 1.025, -0.5)
      this.scene.add(spine)

      const base = new THREE.Mesh(
        new THREE.BoxGeometry(0.6, 0.28, gondolaLength),
        frameMaterial,
      )
      base.position.set(x, 0.14, -0.5)
      this.scene.add(base)

      const margin = (gondolaLength - perLevel * slotWidth) / 2
      for (const side of [-1, 1]) {
        const rows: Slot[][] = []
        const boards: THREE.Mesh[] = []
        for (const level of levels) {
          const board = new THREE.Mesh(
            new THREE.BoxGeometry(0.29, 0.03, gondolaLength),
            shelfMaterial,
          )
          board.position.set(x + side * 0.145, level - 0.015, -0.5)
          this.scene.add(board)
          boards.push(board)

          const row: Slot[] = []
          for (let index = 0; index < perLevel; index++) {
            row.push({
              position: new THREE.Vector3(
                x + side * 0.215,
                level + 0.096,
                zStart + margin + slotWidth * (index + 0.5),
              ),
              facing: new THREE.Vector3(side, 0, 0),
            })
          }
          rows.push(row)
        }
        runs.push({
          levels: rows,
          order: buildRunOrder(rows),
          boards,
          aisle: side < 0 ? unit : unit + 1,
          side: side < 0 ? "right" : "left",
          wallBanner: null,
        })
      }

      this.colliders.push(
        new THREE.Box3(
          new THREE.Vector3(x - 0.34, 0, zStart - 0.1),
          new THREE.Vector3(x + 0.34, 2.1, zStart + gondolaLength + 0.1),
        ),
      )
    }

    const wallShelfLength = width - 2.6
    for (const level of levels) {
      const board = new THREE.Mesh(
        new THREE.BoxGeometry(wallShelfLength, 0.03, 0.34),
        shelfMaterial,
      )
      board.position.set(0, level - 0.015, -depth / 2 + 0.2)
      this.scene.add(board)
    }
    const backing = new THREE.Mesh(
      new THREE.BoxGeometry(wallShelfLength, 2.05, 0.06),
      frameMaterial,
    )
    backing.position.set(0, 1.025, -depth / 2 + 0.05)
    this.scene.add(backing)

    const wallPerLevel = Math.floor(wallShelfLength / slotWidth)
    const wallMargin = (wallShelfLength - wallPerLevel * slotWidth) / 2
    const wallRows: Slot[][] = []
    for (const level of levels) {
      const row: Slot[] = []
      for (let index = 0; index < wallPerLevel; index++) {
        row.push({
          position: new THREE.Vector3(
            -wallShelfLength / 2 + wallMargin + slotWidth * (index + 0.5),
            level + 0.096,
            -depth / 2 + 0.31,
          ),
          facing: new THREE.Vector3(0, 0, 1),
        })
      }
      wallRows.push(row)
    }
    runs.push({
      levels: wallRows,
      order: buildRunOrder(wallRows),
      boards: [],
      aisle: null,
      side: "left",
      wallBanner: {
        position: new THREE.Vector3(0, 2.18, -depth / 2 + 0.33),
        facing: new THREE.Vector3(0, 0, 1),
      },
    })
    this.colliders.push(
      new THREE.Box3(
        new THREE.Vector3(-wallShelfLength / 2, 0, -depth / 2),
        new THREE.Vector3(wallShelfLength / 2, 2.1, -depth / 2 + 0.42),
      ),
    )

    const counter = new THREE.Mesh(
      new THREE.BoxGeometry(2.6, 1.05, 0.7),
      new THREE.MeshStandardMaterial({ color: 0x3b2a44, roughness: 0.6 }),
    )
    counter.position.set(width / 2 - 1.8, 0.525, depth / 2 - 1.3)
    this.scene.add(counter)
    this.colliders.push(new THREE.Box3().setFromObject(counter))

    for (let aisle = 0; aisle <= unitCount; aisle++) {
      const signX = (aisle - unitCount / 2) * 3.3
      const near = new THREE.Mesh(
        new THREE.PlaneGeometry(2.4, 0.56),
        new THREE.MeshBasicMaterial({
          map: createAisleSignTexture([], []),
        }),
      )
      near.position.set(signX, 2.46, -0.5 + gondolaLength / 2 + 0.22)
      const far = new THREE.Mesh(
        new THREE.PlaneGeometry(2.4, 0.56),
        new THREE.MeshBasicMaterial({
          map: createAisleSignTexture([], []),
        }),
      )
      far.position.set(signX, 2.46, -0.5 - gondolaLength / 2 - 0.22)
      far.rotation.y = Math.PI
      this.scene.add(near)
      this.scene.add(far)
      this.aisleSigns.push({ left: [], right: [], near, far })
    }

    const spawn = this.camera.position.clone()
    runs.sort(
      (left, right) =>
        left.levels[left.levels.length - 1][
          left.levels[0].length - 1
        ].position.distanceToSquared(spawn) -
        right.levels[right.levels.length - 1][
          right.levels[0].length - 1
        ].position.distanceToSquared(spawn),
    )

    this.runs = runs
    const wallIndex = runs.findIndex((entry) => entry.wallBanner !== null)
    this.wallRun = runs[wallIndex]
    const wallBanner = this.wallRun.wallBanner
    if (wallBanner) {
      const banner = new THREE.Mesh(
        new THREE.PlaneGeometry(2.4, 0.2),
        new THREE.MeshBasicMaterial({ map: createBannerTexture("Random") }),
      )
      banner.position.copy(wallBanner.position)
      banner.rotation.y = Math.atan2(wallBanner.facing.x, wallBanner.facing.z)
      this.scene.add(banner)
    }

    const spawnPoint = this.camera.position.clone()
    const aisleGroups = new Map<number, number[]>()
    for (let index = 0; index < runs.length; index++) {
      const aisle = runs[index].aisle
      if (aisle === null) continue
      const group = aisleGroups.get(aisle) ?? []
      group.push(index)
      aisleGroups.set(aisle, group)
    }
    const ordered = [...aisleGroups.values()].sort(
      (left, right) =>
        runs[left[0]].order[0].position.distanceToSquared(spawnPoint) -
        runs[right[0]].order[0].position.distanceToSquared(spawnPoint),
    )
    for (const group of ordered) {
      this.aisleStarts.push(this.packOrder.length)
      this.packOrder.push(...group)
    }
  }

  // TODO: Validate
  private refreshSign(sign: AisleSign) {
    const faces: Array<[THREE.Mesh, string[], string[]]> = [
      [sign.near, sign.left, sign.right],
      [sign.far, sign.right, sign.left],
    ]
    for (const [face, left, right] of faces) {
      const material = face.material as THREE.MeshBasicMaterial
      material.map?.dispose()
      material.map = createAisleSignTexture(left, right)
      material.needsUpdate = true
    }
  }

  // TODO: Validate
  addTitles(titles: StoreTitle[]) {
    let added = false
    for (let index = this.placedTitles; index < titles.length; index++) {
      const title = titles[index]
      for (const genre of title.genres.length ? title.genres : ["Unknown"]) {
        const shelved = this.genreCases.get(genre) ?? []
        shelved.push(this.buildCase(title))
        this.genreCases.set(genre, shelved)
        added = true
      }
    }
    this.placedTitles = titles.length

    if (added) {
      this.layoutStore()
      this.layoutWall()
    }
    for (let concurrent = 0; concurrent < 6; concurrent++) this.nextImage()
  }

  // TODO: Validate
  private genreOrder() {
    const named = [...this.genreCases.keys()]
      .filter((genre) => genre !== "Unknown")
      .sort((left, right) => left.localeCompare(right))
    return this.genreCases.has("Unknown") ? [...named, "Unknown"] : named
  }

  // TODO: Validate
  private layoutStore() {
    const entries = this.runs.map(() => [] as string[])
    const sections: Array<{
      run: number
      start: number
      end: number
      genre: string
    }> = []
    let slot = 0
    let cursor = 0
    let tags = 0

    for (const genre of this.genreOrder()) {
      const shelved = this.genreCases.get(genre) ?? []
      if (genre === "Unknown" && cursor > 0) {
        slot = this.aisleStarts.find((start) => start > slot) ?? slot + 1
        cursor = 0
      }
      if (cursor > 0 && slot < this.packOrder.length) {
        const levels = this.runs[this.packOrder[slot]].levels.length
        cursor = Math.ceil(cursor / levels) * levels
      }
      for (const mesh of shelved) {
        while (
          slot < this.packOrder.length &&
          cursor >= this.runs[this.packOrder[slot]].order.length
        ) {
          slot++
          cursor = 0
        }
        if (slot >= this.packOrder.length) break
        const runIndex = this.packOrder[slot]
        const run = this.runs[runIndex]
        const section = sections[sections.length - 1]
        if (!section || section.run !== runIndex || section.genre !== genre) {
          entries[runIndex].push(genre)
          this.settleTag(tags, genre, run.order[cursor])
          tags++
          sections.push({ run: runIndex, start: cursor, end: cursor, genre })
        }
        sections[sections.length - 1].end = cursor
        this.settleCase(mesh, run.order[cursor])
        cursor++
      }
    }

    for (let index = tags; index < this.tagPool.length; index++) {
      this.tagPool[index].visible = false
    }
    this.paintStrips(sections)
    this.postSigns(entries)
  }

  // TODO: Validate
  private paintStrips(
    sections: Array<{ run: number; start: number; end: number; genre: string }>,
  ) {
    let strips = 0
    for (const section of sections) {
      const run = this.runs[section.run]
      const levels = run.levels.length
      const first = Math.floor(section.start / levels)
      const last = Math.floor(section.end / levels)
      for (let level = 0; level < levels; level++) {
        const row = run.levels[level]
        this.settleStrip(
          strips,
          section.genre,
          row[row.length - 1 - first],
          row[row.length - 1 - last],
        )
        strips++
      }
    }
    for (let index = strips; index < this.stripPool.length; index++) {
      this.stripPool[index].visible = false
    }
  }

  // TODO: Validate
  private settleStrip(index: number, genre: string, near: Slot, far: Slot) {
    let mesh = this.stripPool[index]
    if (!mesh) {
      mesh = new THREE.Mesh(this.stripGeometry, this.stripMaterial(genre))
      this.scene.add(mesh)
      this.stripPool.push(mesh)
    }
    mesh.material = this.stripMaterial(genre)
    mesh.visible = true
    mesh.scale.z = Math.abs(near.position.z - far.position.z) + 0.172
    mesh.position
      .copy(near.position)
      .addScaledVector(near.facing, 0.077)
      .setY(near.position.y - 0.104)
      .setZ((near.position.z + far.position.z) / 2)
  }

  // TODO: Validate
  private stripMaterial(genre: string) {
    let material = this.stripMaterials.get(genre)
    if (!material) {
      material = new THREE.MeshStandardMaterial({
        color: new THREE.Color().setHSL(genreHue(genre) / 360, 0.62, 0.46),
        emissive: new THREE.Color().setHSL(genreHue(genre) / 360, 0.62, 0.22),
        roughness: 0.6,
      })
      this.stripMaterials.set(genre, material)
    }
    return material
  }

  // TODO: Validate
  private postSigns(entries: string[][]) {
    for (const sign of this.aisleSigns) {
      sign.left = []
      sign.right = []
    }
    for (let runIndex = 0; runIndex < this.runs.length; runIndex++) {
      const run = this.runs[runIndex]
      if (run.aisle === null) continue
      const sign = this.aisleSigns[run.aisle]
      if (run.side === "left") sign.left = entries[runIndex]
      else sign.right = entries[runIndex]
    }
    for (const sign of this.aisleSigns) this.refreshSign(sign)
  }

  // TODO: Validate
  private settleTag(index: number, genre: string, slot: Slot) {
    let mesh = this.tagPool[index]
    if (!mesh) {
      mesh = new THREE.Mesh(
        this.tagGeometry,
        new THREE.MeshBasicMaterial({ map: createTagTexture(genre) }),
      )
      this.scene.add(mesh)
      this.tagPool.push(mesh)
    }
    const material = mesh.material as THREE.MeshBasicMaterial
    if (material.userData.genre !== genre) {
      material.map?.dispose()
      material.map = createTagTexture(genre)
      material.userData.genre = genre
      material.needsUpdate = true
    }
    mesh.visible = true
    mesh.position
      .copy(slot.position)
      .addScaledVector(slot.facing, 0.077)
      .setY(slot.position.y - 0.117)
    mesh.rotation.y = Math.atan2(slot.facing.x, slot.facing.z)
  }

  // TODO: Validate
  private layoutWall() {
    if (!this.wallRun || this.realCases.length === 0) return
    let index = 0
    for (const slot of this.wallRun.order) {
      this.settleWallCase(index, slot)
      index++
    }
  }

  // TODO: Validate
  private settleWallCase(index: number, slot: Slot) {
    let mesh = this.wallCases[index]
    if (!mesh) {
      mesh = new THREE.Mesh(this.caseGeometry, this.realCases[0].material)
      mesh.rotation.z = (Math.random() - 0.5) * 0.05
      mesh.userData.pick = Math.random()
      this.scene.add(mesh)
      this.caseMeshes.push(mesh)
      this.wallCases.push(mesh)
    }
    const source =
      this.realCases[
        Math.floor((mesh.userData.pick as number) * this.realCases.length)
      ]
    mesh.material = source.material
    mesh.userData = {
      title: source.userData.title as StoreTitle,
      basePosition: slot.position.clone(),
      facing: slot.facing.clone(),
      pick: mesh.userData.pick as number,
    }
    mesh.position.copy(slot.position)
    mesh.rotation.y = Math.atan2(slot.facing.x, slot.facing.z)
  }

  // TODO: Validate
  private settleCase(mesh: THREE.Mesh, slot: Slot) {
    mesh.userData.basePosition = slot.position.clone()
    mesh.userData.facing = slot.facing.clone()
    mesh.position.copy(slot.position)
    if (mesh === this.focused) {
      mesh.position.addScaledVector(slot.facing, 0.04)
    }
    mesh.rotation.y = Math.atan2(slot.facing.x, slot.facing.z)
  }

  // TODO: Validate
  private buildCase(title: StoreTitle) {
    const texture = createCaseTexture(title, null)
    const material = new THREE.MeshStandardMaterial({
      map: texture,
      emissiveMap: texture,
      emissive: 0xffffff,
      emissiveIntensity: 0,
      roughness: 0.42,
      metalness: 0.06,
    })
    const mesh = new THREE.Mesh(this.caseGeometry, material)
    mesh.rotation.z = (Math.random() - 0.5) * 0.05
    mesh.userData = {
      title,
      basePosition: new THREE.Vector3(),
      facing: new THREE.Vector3(0, 0, 1),
    }
    this.scene.add(mesh)
    this.caseMeshes.push(mesh)
    this.realCases.push(mesh)
    if (title.imageUrl) this.queueImage(title, material, mesh)
    return mesh
  }

  // TODO: Validate
  private queueImage(
    title: StoreTitle,
    material: THREE.MeshStandardMaterial,
    mesh: THREE.Mesh,
  ) {
    // TODO: Validate
    const run = () => {
      this.activeImages++
      const image = new Image()
      image.crossOrigin = "anonymous"
      image.referrerPolicy = "no-referrer"
      // TODO: Validate
      const finish = (loaded: HTMLImageElement | null) => {
        if (!this.disposed && loaded) {
          const previous = material.map
          const texture = createCaseTexture(title, loaded)
          material.map = texture
          material.emissiveMap = texture
          material.needsUpdate = true
          previous?.dispose()
        }
        this.activeImages--
        this.nextImage()
      }
      image.onload = () => finish(image)
      image.onerror = () => finish(null)
      image.src = title.imageUrl as string
    }
    this.pendingImages.push({ mesh, run })
  }

  // TODO: Validate
  private nextImage() {
    if (this.disposed || this.activeImages >= 6) return
    if (this.pendingImages.length === 0) return
    let nearest = 0
    let shortest = Number.POSITIVE_INFINITY
    for (let index = 0; index < this.pendingImages.length; index++) {
      const distance = this.pendingImages[
        index
      ].mesh.position.distanceToSquared(this.camera.position)
      if (distance < shortest) {
        shortest = distance
        nearest = index
      }
    }
    this.pendingImages.splice(nearest, 1)[0].run()
  }

  // TODO: Validate
  private handleLock = () => this.callbacks.onLockChange(true)

  // TODO: Validate
  private handleUnlock = () => {
    this.pressed.clear()
    this.velocity.set(0, 0, 0)
    this.callbacks.onLockChange(false)
  }

  // TODO: Validate
  private handleKeyDown = (event: KeyboardEvent) => {
    if (!this.controls.isLocked) return
    this.pressed.add(event.code)
    if (event.code === "KeyE" && this.focused) {
      this.callbacks.onActivate(this.focused.userData.title as StoreTitle)
    }
  }

  // TODO: Validate
  private handleKeyUp = (event: KeyboardEvent) => {
    this.pressed.delete(event.code)
  }

  // TODO: Validate
  private handleMouseDown = () => {
    if (
      this.controls.isLocked &&
      document.pointerLockElement &&
      performance.now() - this.lastExit > 400
    ) {
      this.activateFocused()
    }
  }

  // TODO: Validate
  private handleResize = () => {
    const width = this.container.clientWidth
    const height = this.container.clientHeight
    if (!width || !height) return
    this.camera.aspect = width / height
    this.camera.updateProjectionMatrix()
    this.renderer.setSize(width, height)
  }

  // TODO: Validate
  private blocked(x: number, z: number) {
    for (const box of this.colliders) {
      if (
        x > box.min.x - 0.32 &&
        x < box.max.x + 0.32 &&
        z > box.min.z - 0.32 &&
        z < box.max.z + 0.32
      ) {
        return true
      }
    }
    return false
  }

  // TODO: Validate
  private move(delta: number) {
    const forward = new THREE.Vector3()
    this.camera.getWorldDirection(forward)
    forward.y = 0
    forward.normalize()
    const right = new THREE.Vector3().crossVectors(
      forward,
      new THREE.Vector3(0, 1, 0),
    )

    const direction = new THREE.Vector3()
    if (this.touch) {
      direction.addScaledVector(forward, this.touchMove.y)
      direction.addScaledVector(right, this.touchMove.x)
    }
    if (this.pressed.has("KeyW") || this.pressed.has("ArrowUp")) {
      direction.add(forward)
    }
    if (this.pressed.has("KeyS") || this.pressed.has("ArrowDown")) {
      direction.sub(forward)
    }
    if (this.pressed.has("KeyD") || this.pressed.has("ArrowRight")) {
      direction.add(right)
    }
    if (this.pressed.has("KeyA") || this.pressed.has("ArrowLeft")) {
      direction.sub(right)
    }

    const crouching = this.pressed.has("KeyC") || this.touchCrouch
    const running =
      !crouching &&
      (this.pressed.has("ShiftLeft") ||
        this.pressed.has("ShiftRight") ||
        this.touchRun)
    const speed = crouching ? 1.15 : running ? 5.4 : 2.6
    if (direction.lengthSq() > 0) direction.normalize().multiplyScalar(speed)
    this.velocity.lerp(direction, Math.min(1, delta * 12))

    const position = this.camera.position
    const nextX = THREE.MathUtils.clamp(
      position.x + this.velocity.x * delta,
      -this.limit.x,
      this.limit.x,
    )
    if (!this.blocked(nextX, position.z)) position.x = nextX
    const nextZ = THREE.MathUtils.clamp(
      position.z + this.velocity.z * delta,
      -this.limit.y,
      this.limit.y,
    )
    if (!this.blocked(position.x, nextZ)) position.z = nextZ

    this.eyeHeight = THREE.MathUtils.damp(
      this.eyeHeight,
      crouching ? 0.78 : 1.65,
      11,
      delta,
    )
    const moving = this.velocity.length() > 0.4
    const bob = crouching ? 0.009 : 0.02
    position.y =
      this.eyeHeight + (moving ? Math.sin(performance.now() / 145) * bob : 0)
  }

  // TODO: Validate
  private updateFocus() {
    this.applyFocus(this.pick(0, 0, 3.2))
  }

  // TODO: Validate
  private pick(x: number, y: number, far: number) {
    this.raycaster.setFromCamera(new THREE.Vector2(x, y), this.camera)
    this.raycaster.far = far
    const hit = this.raycaster.intersectObjects(this.caseMeshes, false)[0]
    return (hit?.object as THREE.Mesh | undefined) ?? null
  }

  // TODO: Validate
  private applyFocus(mesh: THREE.Mesh | null) {
    if (mesh === this.focused) return
    if (this.focused) {
      const material = this.focused.material as THREE.MeshStandardMaterial
      material.emissiveIntensity = 0
      this.focused.position.copy(
        this.focused.userData.basePosition as THREE.Vector3,
      )
    }
    this.focused = mesh
    if (!mesh) {
      this.callbacks.onFocus(null)
      return
    }
    const material = mesh.material as THREE.MeshStandardMaterial
    material.emissiveIntensity = 0.3
    mesh.position
      .copy(mesh.userData.basePosition as THREE.Vector3)
      .addScaledVector(mesh.userData.facing as THREE.Vector3, 0.04)
    this.callbacks.onFocus(mesh.userData.title as StoreTitle)
  }

  // TODO: Validate
  private tick = () => {
    if (this.disposed) return
    this.animationHandle = requestAnimationFrame(this.tick)
    const delta = Math.min(this.clock.getDelta(), 0.1)
    if (this.touch ? this.touchActive : this.controls.isLocked) {
      this.move(delta)
      if (!this.touch) this.updateFocus()
    }
    this.renderer.render(this.scene, this.camera)
  }

  // TODO: Validate
  lock() {
    if (!this.touch) {
      if (performance.now() - this.lastExit < 900) return
      this.controls.lock()
      return
    }
    this.touchActive = true
    this.callbacks.onLockChange(true)
  }

  // TODO: Validate
  exit() {
    if (!this.touch) {
      this.lastExit = performance.now()
      this.controls.unlock()
      return
    }
    this.touchActive = false
    this.touchMove.set(0, 0)
    this.velocity.set(0, 0, 0)
    this.callbacks.onLockChange(false)
  }

  // TODO: Validate
  setMove(x: number, y: number, running: boolean) {
    this.touchMove.set(x, y)
    this.touchRun = running
  }

  // TODO: Validate
  setCrouch(crouching: boolean) {
    this.touchCrouch = crouching
  }

  // TODO: Validate
  look(deltaX: number, deltaY: number) {
    this.euler.setFromQuaternion(this.camera.quaternion)
    this.euler.y -= deltaX * 0.005
    this.euler.x = THREE.MathUtils.clamp(
      this.euler.x - deltaY * 0.005,
      -Math.PI / 2 + 0.05,
      Math.PI / 2 - 0.05,
    )
    this.camera.quaternion.setFromEuler(this.euler)
  }

  // TODO: Validate
  focusAt(clientX: number, clientY: number) {
    const rect = this.renderer.domElement.getBoundingClientRect()
    this.applyFocus(
      this.pick(
        ((clientX - rect.left) / rect.width) * 2 - 1,
        -((clientY - rect.top) / rect.height) * 2 + 1,
        4.5,
      ),
    )
  }

  // TODO: Validate
  activateFocused() {
    if (!this.focused) return
    const title = this.focused.userData.title as StoreTitle
    this.applyFocus(null)
    this.exit()
    this.callbacks.onActivate(title)
  }

  // TODO: Validate
  dispose() {
    this.disposed = true
    cancelAnimationFrame(this.animationHandle)
    this.resizeObserver.disconnect()
    this.controls.removeEventListener("lock", this.handleLock)
    this.controls.removeEventListener("unlock", this.handleUnlock)
    this.controls.disconnect()
    window.removeEventListener("keydown", this.handleKeyDown)
    window.removeEventListener("keyup", this.handleKeyUp)
    window.removeEventListener("mousedown", this.handleMouseDown)
    this.scene.traverse((object) => {
      const mesh = object as THREE.Mesh
      if (!mesh.isMesh) return
      mesh.geometry.dispose()
      const materials = Array.isArray(mesh.material)
        ? mesh.material
        : [mesh.material]
      for (const entry of materials) {
        const material = entry as THREE.MeshStandardMaterial
        material.map?.dispose()
        material.dispose()
      }
    })
    this.caseGeometry.dispose()
    this.tagGeometry.dispose()
    this.stripGeometry.dispose()
    this.renderer.dispose()
    this.renderer.domElement.remove()
  }
}
