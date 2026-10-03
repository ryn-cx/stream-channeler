// TODO: Validate
import * as THREE from "three"
import { CarGenerator } from "three/addons/generators/city/CarGenerator.js"
import { SidewalkGenerator } from "three/addons/generators/city/SidewalkGenerator.js"
import { StreetlightGenerator } from "three/addons/generators/city/StreetlightGenerator.js"
import { StreetTreeGenerator } from "three/addons/generators/city/StreetTreeGenerator.js"
import { ForestGenerator } from "three/addons/generators/ForestGenerator.js"
import { TerrainGenerator } from "three/addons/generators/TerrainGenerator.js"
import Stats from "three/addons/libs/stats.module.js"
import { WoodNodeMaterial } from "three/addons/materials/WoodNodeMaterial.js"
import { PointerLockControls } from "three/examples/jsm/controls/PointerLockControls.js"
import { color, mix, mx_noise_float, positionLocal, vec3 } from "three/tsl"
import { WebGPURenderer } from "three/webgpu"
import {
  createAisleSignTexture,
  createCarpetTexture,
  createCaseCanvas,
  createCaseTexture,
  createCeilingTexture,
  createDiffuserTexture,
  createFilterBoardTexture,
  createGlowTexture,
  createGrassTexture,
  createLabelTexture,
  createLoaderTexture,
  createLotTexture,
  createRippleTexture,
  createStoreSignTexture,
  createTagTexture,
  genreHue,
  type StoreTitle,
  shelfGenres,
} from "./caseTexture"
import { loadStoreImage } from "./storeImage"
import { fetchTitleDetail } from "./titleDetail"

type Slot = { position: THREE.Vector3; facing: THREE.Vector3 }

type ShelfRun = {
  levels: Slot[][]
  order: Slot[]
  aisle: number | null
  side: "left" | "right"
}

type AisleSign = {
  left: string[]
  right: string[]
  near: THREE.Mesh
  far: THREE.Mesh
  group: THREE.Group
  anchor: THREE.Vector3
  dirty: boolean
}

// TODO: Validate
const randomOffset = () =>
  new THREE.Vector3(
    Math.random() - 0.5,
    Math.random() - 0.5,
    Math.random() - 0.5,
  )

// TODO: Validate
const seededOffset = (seed: string) => {
  let hash = 2166136261
  for (let index = 0; index < seed.length; index++) {
    hash ^= seed.charCodeAt(index)
    hash = Math.imul(hash, 16777619)
  }
  const axis = (shift: number) => ((hash >>> shift) & 1023) / 1023 - 0.5
  return new THREE.Vector3(axis(0), axis(10), axis(20))
}

// TODO: Validate
export const isTouchDevice = () =>
  window.matchMedia("(pointer: coarse)").matches

// TODO: Validate
export const shelfSlots = (
  titles: StoreTitle[],
  allowed: Set<string> | null,
) => {
  const counts = new Map<string, number>()
  for (const title of titles) {
    const genreNames = shelfGenres(title, allowed)
    if (genreNames.length === 0 && title.genres.length > 0) continue
    for (const genre of genreNames.length ? genreNames : ["Unknown"]) {
      counts.set(genre, (counts.get(genre) ?? 0) + 1)
    }
  }
  const unknown = counts.get("Unknown") ?? 0
  counts.delete("Unknown")
  const named = [...counts.values()].reduce(
    (total, count) => total + Math.ceil(count / 5) * 5,
    0,
  )
  const namedRuns = Math.ceil(named / 250)
  const unknownStart =
    unknown > 0 && namedRuns > 0 ? namedRuns + 1 - (namedRuns % 2) : namedRuns
  return (unknownStart + Math.ceil(unknown / 250)) * 250
}

export type StoreProgress =
  | { stage: "building" }
  | { stage: "starting" }
  | { stage: "compiling"; compiled: number; total: number }
  | { stage: "ready" }

export type VideoStoreCallbacks = {
  onFocus: (title: StoreTitle | null) => void
  onActivate: (title: StoreTitle) => void
  onChannelAction: (action: "create" | "add") => void
  onFilters: () => void
  onLockChange: (locked: boolean) => void
  onProgress: (progress: StoreProgress) => void
  onCovers: (pending: number) => void
}

// TODO: Validate
const buildCaseGeometry = (width = 0.135, height = 0.19, depth = 0.015) => {
  const geometry = new THREE.BoxGeometry(width, height, depth)
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
  private renderer: WebGPURenderer
  private cars: CarGenerator | null = null
  private litCars: CarGenerator | null = null
  private carFleet: THREE.Group | null = null
  private litFleet: THREE.Group | null = null
  private parked: Array<{
    x: number
    z: number
    turn: number
    spin: THREE.Vector3
    drift: THREE.Vector3
    color: number
    lit: boolean
  }> = []
  private sidewalk: SidewalkGenerator | null = null
  private dressed = new WeakSet<THREE.Material>()
  private moonLight = new THREE.DirectionalLight(0xaebede, 0.55)
  private skyLight = new THREE.HemisphereLight(0x33425f, 0x05060a, 0.5)
  private poolMaterial: THREE.MeshBasicMaterial | null = null
  private trees: StreetTreeGenerator | null = null
  private forest: ForestGenerator | null = null
  private terrain: TerrainGenerator | null = null
  private lamps: StreetlightGenerator | null = null
  private rain: THREE.LineSegments | null = null
  private splashes: THREE.InstancedMesh | null = null
  private ripples: Array<{ x: number; y: number; z: number; age: number }> = []
  private rippleCursor = 0
  private rainSpeed = 14
  private rainSpanX = 0
  private rainSpanZ = 0
  private rainCenterZ = 0
  private rainRoofX = 0
  private rainRoofZ = 0
  private scene = new THREE.Scene()
  private camera: THREE.PerspectiveCamera
  private controls: PointerLockControls
  private clock = new THREE.Clock()
  private raycaster = new THREE.Raycaster()
  private pressed = new Set<string>()
  private colliders: THREE.Box3[] = []
  private focused: THREE.Mesh | null = null
  private velocity = new THREE.Vector3()
  private eyeHeight = 1.65
  private animationHandle = 0
  private disposed = false
  private pendingImages: Array<{ mesh: THREE.Mesh; run: () => void }> = []
  private activeImages = 0
  private reportedCovers = 0
  private storeSigns: THREE.Mesh[] = []
  private runs: ShelfRun[] = []
  private aisleSigns: AisleSign[] = []
  private packOrder: number[] = []
  private aisleStarts: number[] = []
  private posters: THREE.Mesh[] = []
  private counterTop = new THREE.Vector3()
  private counterRows: THREE.Vector3[] = []
  private counterStep = 0
  private counterCapacity = 0
  private counterCases: THREE.Mesh[] = []
  private channelButtons: THREE.Mesh[] = []
  private doorLeaves: Array<{
    group: THREE.Group
    swing: number
    open: boolean
  }> = []
  private filterBoard: THREE.Mesh | null = null
  private swatches: THREE.Mesh[] = []
  private caseMaterials = new Set<
    THREE.MeshStandardMaterial | THREE.MeshBasicMaterial
  >()
  private unlit = true
  private reflections = true
  private format = 0
  private caseScale = 1
  private askew = 0.5
  private lightLevel = 1
  private fullPosters = false
  private shelfStart = 0
  private shelfEnd = 0
  private lampPool: THREE.PointLight[] = []
  private lampAnchors: THREE.Vector3[] = []
  private laneGlows: THREE.Mesh[] = []
  private glowMaterial: THREE.MeshBasicMaterial | null = null
  private diffuserMaterial: THREE.MeshBasicMaterial | null = null
  private ceilingMaterial: THREE.MeshStandardMaterial | null = null
  private floorMaterial: THREE.MeshStandardMaterial | null = null
  private carpetRepeat = new THREE.Vector2(20, 20)
  private roomMaterials: THREE.MeshStandardMaterial[] = []
  private runMeshes: THREE.Mesh[][] = []
  private loaderButtons: THREE.Mesh[] = []
  private revealedRuns = new Set<number>()
  private allTitles: StoreTitle[] = []
  private genreTitles = new Map<string, StoreTitle[]>()
  private runTitles: StoreTitle[][] = []
  private runSlots: number[][] = []
  private runGroups: THREE.Group[] = []
  private caseGroups: THREE.Group[] = []
  private casePool: THREE.Mesh[] = []
  private mountedRuns = new Set<number>()
  private generationCounter = 0
  private tagPool: THREE.Mesh[] = []
  private tagGeometry = new THREE.PlaneGeometry(0.155, 0.042)
  private tagMaterials = new Map<string, THREE.MeshBasicMaterial>()
  private stripMaterials = new Map<string, THREE.MeshStandardMaterial>()
  private placeholderMaterials = new Map<number, THREE.MeshStandardMaterial>()
  private blocks: THREE.InstancedMesh | null = null
  private blockPlacements: THREE.Matrix4[][] = []
  private instanced: THREE.InstancedMesh[] = []
  private shelves: THREE.InstancedMesh[] = []
  private runCenters: THREE.Vector3[] = []
  private nearRuns = new Set<number>()
  private visibleRuns = new Set<number>()
  private visibleSigns = new Set<number>()
  private viewRange = Number.POSITIVE_INFINITY
  private scratch = new THREE.Vector3()
  private lastFocusAt = new THREE.Vector3(Number.NaN, 0, 0)
  private lastFocusTurn = new THREE.Quaternion()
  private lodCountdown = 0
  private blockMaterial = new THREE.MeshStandardMaterial({
    color: 0x24242c,
    roughness: 0.75,
    metalness: 0.05,
  })
  private highlightMaterial = this.trackCase(
    new THREE.MeshStandardMaterial({
      emissive: 0xffffff,
      emissiveIntensity: 0.3,
      roughness: 0.42,
      metalness: 0.06,
    }),
  )
  private batchMaterial = this.trackCase(
    new THREE.MeshStandardMaterial({ roughness: 0.55, metalness: 0.04 }),
  )
  private runBatches = new Map<number, THREE.InstancedMesh>()
  private hiddenInstance = new THREE.Matrix4().makeScale(0, 0, 0)
  private loadCoversMaterial = new THREE.MeshBasicMaterial({
    map: createLoaderTexture("LOAD COVERS"),
  })
  private unloadCoversMaterial = new THREE.MeshBasicMaterial({
    map: createLoaderTexture("UNLOAD COVERS"),
  })
  private stripPool: THREE.Mesh[] = []
  private stripGeometry = new THREE.BoxGeometry(0.014, 0.018, 1)
  private placedTitles = 0
  private restocked = false
  private shelfFilter: Set<string> | null = null
  private touchMove = new THREE.Vector2()
  private touchRun = false
  private touchCrouch = false
  private touchActive = false
  private lastExit = 0
  private euler = new THREE.Euler(0, 0, 0, "YXZ")
  readonly touch = isTouchDevice()
  private caseGeometry = buildCaseGeometry()
  private resizeObserver: ResizeObserver
  private metadata: "tmdb" | "source"
  private stats = new Stats()
  private drawCallPanel = new Stats.Panel("CALLS", "#ff8", "#221")
  private statsPanel = document.createElement("div")
  private drawCallsShownAt = 0
  private drawCallPeak = 0

  // TODO: Validate
  constructor(
    container: HTMLElement,
    slotCount: number,
    storeName: string,
    metadata: "tmdb" | "source",
    callbacks: VideoStoreCallbacks,
  ) {
    this.container = container
    this.metadata = metadata
    this.callbacks = callbacks

    this.renderer = new WebGPURenderer({ antialias: true })
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
    this.renderer.setSize(container.clientWidth, container.clientHeight)
    this.renderer.sortObjects = false
    this.renderer.toneMapping = THREE.ACESFilmicToneMapping
    this.renderer.toneMappingExposure = 1
    this.renderer.info.autoReset = false
    container.appendChild(this.renderer.domElement)
    this.statsPanel.style.cssText =
      "position:absolute;right:0;bottom:0;display:none;gap:2px;opacity:0.9;z-index:10"
    this.stats.dom.style.cssText = "cursor:pointer"
    this.statsPanel.append(this.drawCallPanel.dom, this.stats.dom)
    container.appendChild(this.statsPanel)

    this.scene.background = new THREE.Color(0x07070b)

    this.camera = new THREE.PerspectiveCamera(
      72,
      container.clientWidth / container.clientHeight,
      0.05,
      420,
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

    this.callbacks.onProgress({ stage: "starting" })
    void this.start()
  }

  // TODO: Validate
  private async start() {
    await this.renderer.init()
    if (this.disposed) return
    const warmLayer = 30
    const warmCamera = this.camera.clone()
    warmCamera.layers.set(warmLayer)
    const pending: Array<[THREE.Object3D, number]> = []
    this.scene.traverse((object) => {
      if ((object as THREE.Light).isLight) object.layers.enable(warmLayer)
      if (!(object as THREE.Mesh).material) return
      if (!object.visible || object.layers.mask === 0) return
      pending.push([object, object.layers.mask])
      object.layers.disableAll()
    })
    const spawn = this.camera.position.clone()
    // TODO: Validate
    const distance = (object: THREE.Object3D) =>
      object.getWorldPosition(new THREE.Vector3()).distanceToSquared(spawn)
    pending.sort(([left], [right]) => distance(left) - distance(right))
    this.animationHandle = requestAnimationFrame(this.tick)
    for (const [index, [object, mask]] of pending.entries()) {
      if (this.disposed) return
      this.callbacks.onProgress({
        stage: "compiling",
        compiled: index,
        total: pending.length,
      })
      const culled = object.frustumCulled
      object.layers.set(warmLayer)
      object.frustumCulled = false
      await this.renderer.compileAsync(object, warmCamera, this.scene)
      object.frustumCulled = culled
      object.layers.mask = mask
    }
    if (this.disposed) return
    this.callbacks.onProgress({ stage: "ready" })
  }

  // TODO: Validate
  setStoreName(storeName: string) {
    for (const sign of this.storeSigns) {
      const material = sign.material as THREE.MeshBasicMaterial
      material.map?.dispose()
      material.map = createStoreSignTexture(storeName)
      material.needsUpdate = true
    }
  }

  // TODO: Validate
  private buildStore(slotCount: number, storeName: string) {
    const levels = [0.32, 0.68, 1.04, 1.4, 1.76]
    const slotWidth = 0.172
    const perLevel = 50
    const gondolaLength = perLevel * slotWidth
    const sides = Math.max(2, Math.ceil(slotCount / (levels.length * perLevel)))
    const unitCount = Math.min(400, Math.max(1, Math.ceil(sides / 2)))
    const width = unitCount * 2 + 2.9
    const depth = gondolaLength + 6
    this.camera.position.set(width / 2 - 1.8, 1.65, depth / 2 - 1.05)
    this.camera.lookAt(-width / 2 + 1.2, 1.3, -depth / 2 + 1.2)

    this.setFog(100)

    this.carpetRepeat.set(width / 1.5, depth / 1.5)
    this.floorMaterial = new THREE.MeshStandardMaterial({
      map: createCarpetTexture(),
      color: 0xbababa,
      roughness: 1,
      metalness: 0,
    })
    this.floorMaterial.map?.repeat.copy(this.carpetRepeat)
    const floor = new THREE.Mesh(
      new THREE.PlaneGeometry(width, depth),
      this.floorMaterial,
    )
    floor.rotation.x = -Math.PI / 2
    this.scene.add(floor)

    const columns = Math.max(1, Math.round(width / 0.61))
    const rows = Math.max(1, Math.round(depth / 1.22))
    const tileX = width / columns
    const tileZ = depth / rows
    const ceilingTexture = createCeilingTexture()
    ceilingTexture.repeat.set(columns, rows)
    this.ceilingMaterial = new THREE.MeshStandardMaterial({
      map: ceilingTexture,
      emissiveMap: ceilingTexture,
      color: 0x9a9a9a,
      roughness: 1,
    })
    const ceiling = new THREE.Mesh(
      new THREE.PlaneGeometry(width, depth),
      this.ceilingMaterial,
    )
    ceiling.rotation.x = Math.PI / 2
    ceiling.position.y = 3.2
    this.scene.add(ceiling)

    const wallMaterial = new THREE.MeshStandardMaterial({
      color: 0xd8b13a,
      roughness: 0.9,
      side: THREE.DoubleSide,
    })
    const walls: Array<[number, number, number, number]> = [
      [0, -depth / 2, width, 0],
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

    this.moonLight.position.set(-70, 90, depth / 2 + 120)
    this.moonLight.target.position.set(0, 0, depth / 2 + 30)
    this.scene.add(this.moonLight)
    this.scene.add(this.moonLight.target)
    this.scene.add(this.skyLight)

    const bays = Math.max(4, Math.round(width / 1.3))
    const bayWidth = width / bays
    const doorBay = Math.min(
      bays - 2,
      Math.max(0, Math.round((width - 6.6) / bayWidth) - 1),
    )
    const doorCenter = -width / 2 + bayWidth * (doorBay + 1)

    for (const [minX, minZ, maxX, maxZ] of [
      [-width / 2 - 0.2, -depth / 2 - 0.2, width / 2 + 0.2, -depth / 2],
      [-width / 2 - 0.2, -depth / 2, -width / 2, depth / 2],
      [width / 2, -depth / 2, width / 2 + 0.2, depth / 2],
      [-width / 2, depth / 2, doorCenter - bayWidth, depth / 2 + 0.2],
      [doorCenter + bayWidth, depth / 2, width / 2, depth / 2 + 0.2],
    ] as const) {
      if (maxX - minX < 0.01) continue
      this.colliders.push(
        new THREE.Box3(
          new THREE.Vector3(minX, 0, minZ),
          new THREE.Vector3(maxX, 3.2, maxZ),
        ),
      )
    }

    const glassMaterial = new THREE.MeshBasicMaterial({
      color: 0x7d98ad,
      transparent: true,
      opacity: 0.16,
      side: THREE.DoubleSide,
      depthWrite: false,
    })
    const doorFrameMaterial = new THREE.MeshBasicMaterial({ color: 0x24262d })

    const header = new THREE.Mesh(
      new THREE.PlaneGeometry(width, 0.8),
      wallMaterial,
    )
    header.position.set(0, 2.8, depth / 2)
    header.rotation.y = Math.PI
    this.scene.add(header)

    for (const [side, span] of [
      [-1, bayWidth * doorBay],
      [1, bayWidth * (bays - doorBay - 2)],
    ] as const) {
      if (span < 0.02) continue
      const x = side * (width / 2 - span / 2)
      const bulkhead = new THREE.Mesh(
        new THREE.PlaneGeometry(span, 0.35),
        wallMaterial,
      )
      bulkhead.position.set(x, 0.175, depth / 2)
      bulkhead.rotation.y = Math.PI
      this.scene.add(bulkhead)

      const glazing = new THREE.Mesh(
        new THREE.PlaneGeometry(span, 2.05),
        glassMaterial,
      )
      glazing.position.set(x, 1.375, depth / 2 - 0.04)
      this.scene.add(glazing)

      const sill = new THREE.Mesh(
        new THREE.BoxGeometry(span, 0.08, 0.09),
        doorFrameMaterial,
      )
      sill.position.set(x, 0.36, depth / 2 - 0.04)
      this.scene.add(sill)
    }

    const head = new THREE.Mesh(
      new THREE.BoxGeometry(width, 0.1, 0.09),
      doorFrameMaterial,
    )
    head.position.set(0, 2.4, depth / 2 - 0.04)
    this.scene.add(head)

    for (let bay = 1; bay < bays; bay++) {
      if (bay >= doorBay && bay <= doorBay + 2) continue
      const x = -width / 2 + bayWidth * bay
      const divider = new THREE.Mesh(
        new THREE.BoxGeometry(0.07, 2.05, 0.09),
        doorFrameMaterial,
      )
      divider.position.set(x, 1.375, depth / 2 - 0.04)
      this.scene.add(divider)
    }

    for (const side of [-1, 1]) {
      const jamb = new THREE.Mesh(
        new THREE.BoxGeometry(0.07, 2.4, 0.1),
        doorFrameMaterial,
      )
      jamb.position.set(doorCenter + side * bayWidth, 1.2, depth / 2 - 0.06)
      this.scene.add(jamb)

      const leaf = new THREE.Group()
      leaf.position.set(doorCenter + side * bayWidth, 1.2, depth / 2 - 0.06)
      this.scene.add(leaf)
      const index = this.doorLeaves.length
      this.doorLeaves.push({
        group: leaf,
        swing: (side * Math.PI) / 2,
        open: false,
      })

      const pane = new THREE.Mesh(
        new THREE.PlaneGeometry(bayWidth * 0.94, 2.4),
        glassMaterial,
      )
      pane.position.set((-side * bayWidth) / 2, 0, 0)
      pane.userData = { toggle: "door", leaf: index }
      leaf.add(pane)
      this.swatches.push(pane)

      const edge = new THREE.Mesh(
        new THREE.BoxGeometry(0.06, 2.4, 0.1),
        doorFrameMaterial,
      )
      edge.position.set(-side * bayWidth * 0.97, 0, 0)
      edge.userData = { toggle: "door", leaf: index }
      leaf.add(edge)
      this.swatches.push(edge)

      const handle = new THREE.Mesh(
        new THREE.BoxGeometry(0.05, 0.62, 0.05),
        doorFrameMaterial,
      )
      handle.position.set(-side * bayWidth * 0.82, -0.15, -0.09)
      handle.userData = { toggle: "door", leaf: index }
      leaf.add(handle)
      this.swatches.push(handle)
    }

    const lotUnits = Math.max(1, Math.round(width / 19.9))
    const lotWidth = lotUnits * 19.9
    this.rainSpanX = Math.max(width, lotWidth)
    this.rainSpanZ = depth + 50
    this.rainCenterZ = 25
    this.rainRoofX = width / 2
    this.rainRoofZ = depth / 2
    const streaks = new Float32Array(20000 * 6)
    for (let drop = 0; drop < 20000; drop++) {
      this.seedDrop(streaks, drop * 6, Math.random() * 26)
    }
    const rainGeometry = new THREE.BufferGeometry()
    rainGeometry.setAttribute("position", new THREE.BufferAttribute(streaks, 3))
    rainGeometry.setDrawRange(0, 0)
    this.rain = new THREE.LineSegments(
      rainGeometry,
      new THREE.LineBasicMaterial({
        color: 0xc4dcff,
        transparent: true,
        opacity: 0.5,
        depthWrite: false,
        fog: false,
      }),
    )
    this.rain.frustumCulled = false
    this.scene.add(this.rain)

    for (let ripple = 0; ripple < 500; ripple++) {
      this.ripples.push({ x: 0, y: 0, z: 0, age: 1 })
    }
    this.splashes = new THREE.InstancedMesh(
      new THREE.PlaneGeometry(1, 1).rotateX(-Math.PI / 2),
      new THREE.MeshBasicMaterial({
        map: createRippleTexture(),
        transparent: true,
        blending: THREE.AdditiveBlending,
        depthWrite: false,
        fog: false,
      }),
      500,
    )
    const resting = new THREE.Matrix4()
    const unlit = new THREE.Color(0, 0, 0)
    for (let ripple = 0; ripple < 500; ripple++) {
      this.splashes.setMatrixAt(ripple, resting)
      this.splashes.setColorAt(ripple, unlit)
    }
    this.splashes.frustumCulled = false
    this.splashes.count = 0
    this.scene.add(this.splashes)

    const domeMaterial = new THREE.MeshBasicMaterial({
      side: THREE.BackSide,
      depthWrite: false,
      fog: false,
    })
    const skyDirection = positionLocal.normalize()
    const clusters = mx_noise_float(
      skyDirection.mul(3.2).add(vec3(13.7, 5.1, 21.3)),
    )
    const speckle = mx_noise_float(skyDirection.mul(210))
    const starfield = clusters
      .abs()
      .pow(1 / 0.2)
      .abs()
      .add(speckle)
      .abs()
      .pow(1 / 0.042)
      .abs()
      .clamp(0, 1)
    const horizon = skyDirection.y.mul(0.5).add(0.5)
    domeMaterial.colorNode = mix(color(0x22324c), color(0x03040c), horizon).add(
      color(0xeaf1ff).mul(starfield),
    )
    const dome = new THREE.Mesh(
      new THREE.SphereGeometry(360, 64, 40),
      domeMaterial,
    )
    dome.position.set(0, -12, depth / 2 + 20)
    dome.renderOrder = -1
    this.scene.add(dome)

    const apron = new THREE.Mesh(
      new THREE.PlaneGeometry(lotWidth + 60, 84),
      new THREE.MeshBasicMaterial({ color: 0x101016, fog: false }),
    )
    apron.position.set(0, -0.12, depth / 2 + 42)
    apron.rotation.x = -Math.PI / 2
    this.scene.add(apron)

    this.sidewalk = new SidewalkGenerator({
      width: Math.max(width, lotWidth),
      depth: 2.3,
      height: 0.15,
      radius: 0.6,
    })
    const walk = this.sidewalk.build([
      new THREE.Matrix4().makeTranslation(0, -0.12, depth / 2 + 1.15),
    ])
    this.dressOutdoors(walk)
    this.scene.add(walk)

    const nearBays = createLotTexture(false)
    nearBays.repeat.set(lotWidth / 2.6, 1)
    const nearLot = new THREE.Mesh(
      new THREE.PlaneGeometry(lotWidth, 5.2),
      new THREE.MeshBasicMaterial({ map: nearBays, fog: false }),
    )
    nearLot.position.set(0, -0.1, depth / 2 + 4.9)
    nearLot.rotation.x = -Math.PI / 2
    this.scene.add(nearLot)

    for (let spot = 0; spot < Math.floor(lotWidth / 2.6); spot++) {
      if (Math.random() < 0.5) continue
      this.parked.push({
        x: -lotWidth / 2 + 2.6 * (spot + 0.5),
        z: depth / 2 + 4.9,
        turn: Math.random() < 0.7 ? Math.PI : 0,
        spin: randomOffset(),
        drift: randomOffset(),
        lit: Math.random() < 0.1,
        color:
          Math.random() < 0.15
            ? CarGenerator.taxiColor
            : [0x9aa3ad, 0x2f3a4a, 0x7d2b2b, 0xd7d9dc, 0x1d2126, 0x35543f][
                Math.floor(Math.random() * 6)
              ],
      })
    }

    const farBays = createLotTexture(true)
    farBays.repeat.set(1, 13)
    const farBayMaterial = new THREE.MeshBasicMaterial({
      map: farBays,
      fog: false,
    })
    const farBayGeometry = new THREE.PlaneGeometry(5.2, 34)
    const grassTexture = createGrassTexture()
    grassTexture.repeat.set(1.5, 17)
    const grassMaterial = new THREE.MeshBasicMaterial({
      map: grassTexture,
      fog: false,
    })
    const islandGeometry = new THREE.PlaneGeometry(3, 34)
    const islandXs: number[] = []
    let cursor = -lotWidth / 2
    for (let unit = 0; unit < lotUnits; unit++) {
      for (const [kind, span] of [
        ["bay", 5.2],
        ["aisle", 6.5],
        ["bay", 5.2],
        ["grass", 3],
      ] as const) {
        const x = cursor + span / 2
        cursor += span
        if (kind === "aisle") continue
        const strip = new THREE.Mesh(
          kind === "bay" ? farBayGeometry : islandGeometry,
          kind === "bay" ? farBayMaterial : grassMaterial,
        )
        strip.position.set(x, kind === "bay" ? -0.1 : -0.06, depth / 2 + 31)
        strip.rotation.x = -Math.PI / 2
        this.scene.add(strip)
        if (kind === "grass") islandXs.push(x)
        if (kind !== "bay") continue
        for (let stall = 0; stall < 12; stall++) {
          if (Math.random() < 0.55) continue
          this.parked.push({
            x,
            z: depth / 2 + 15.3 + stall * 2.6,
            turn: (Math.random() < 0.5 ? 1 : -1) * (Math.PI / 2),
            spin: randomOffset(),
            drift: randomOffset(),
            lit: Math.random() < 0.1,
            color:
              Math.random() < 0.12
                ? CarGenerator.taxiColor
                : [0x9aa3ad, 0x2f3a4a, 0x7d2b2b, 0xd7d9dc, 0x1d2126, 0x35543f][
                    Math.floor(Math.random() * 6)
                  ],
          })
        }
      }
    }

    this.poolMaterial = new THREE.MeshBasicMaterial({
      map: createGlowTexture(),
      transparent: true,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
      opacity: 0.25,
      fog: false,
    })
    const poolMaterial = this.poolMaterial
    const treePlacements: THREE.Matrix4[] = []
    const lampPlacements: THREE.Matrix4[] = []
    for (const islandX of islandXs) {
      for (let spot = 0; spot < 9; spot++) {
        const z = depth / 2 + 16 + spot * 3.75
        if (spot % 2 === 0) {
          treePlacements.push(
            new THREE.Matrix4()
              .makeRotationY(Math.random() * Math.PI * 2)
              .setPosition(islandX, -0.06, z),
          )
        } else {
          for (const turn of [Math.PI / 2, -Math.PI / 2]) {
            lampPlacements.push(
              new THREE.Matrix4()
                .makeRotationY(turn)
                .setPosition(islandX, -0.06, z),
            )
          }
        }
      }
    }

    if (this.parked.length > 0) {
      this.cars = new CarGenerator()
      this.litCars = new CarGenerator()
      this.parkCars()
    }

    this.terrain = new TerrainGenerator({
      seed: Math.floor(Math.random() * 1000),
      size: 900,
      segments: 256,
      heightScale: 34,
      frequency: 0.004,
      talusPasses: 8,
    })
    const ground = this.terrain.build()
    this.levelTerrain(
      this.terrain,
      lotWidth / 2 + 42,
      -depth / 2 - 30,
      depth / 2 + 95,
      90,
    )
    ground.position.y = -0.2
    this.dressOutdoors(ground)
    this.scene.add(ground)

    this.forest = new ForestGenerator({
      seed: Math.floor(Math.random() * 1000),
      count: 42000,
      altitudeMin: 0.02,
      altitudeMax: 1,
      minSlope: 0,
      densityFrequency: 0.02,
      from: 190,
      to: 380,
    })
    const woodland = this.forest.build(this.terrain)
    woodland.position.y = -0.2
    this.dressOutdoors(woodland)
    this.scene.add(woodland)

    this.trees = new StreetTreeGenerator()
    const grove = this.trees.build(treePlacements)
    this.dressOutdoors(grove)
    this.scene.add(grove)

    this.lamps = new StreetlightGenerator({ height: 5.6, reach: 1.8 })
    const posts = this.lamps.build(lampPlacements)
    this.dressOutdoors(posts)
    this.scene.add(posts)

    const poolGeometry = new THREE.CircleGeometry(2.6, 24)
    const lampHead = new THREE.Vector3(
      0,
      this.lamps.parameters.height,
      this.lamps.parameters.reach,
    )
    for (const placement of lampPlacements) {
      const lamp = lampHead.clone().applyMatrix4(placement)
      const pool = new THREE.Mesh(poolGeometry, poolMaterial)
      pool.position.set(lamp.x, -0.08, lamp.z)
      pool.rotation.x = -Math.PI / 2
      this.scene.add(pool)
    }

    const housingMaterial = new THREE.MeshStandardMaterial({
      color: 0x3c3f47,
      roughness: 0.55,
      metalness: 0.35,
    })
    this.diffuserMaterial = new THREE.MeshBasicMaterial({
      map: createDiffuserTexture(),
      toneMapped: false,
    })
    const diffuserMaterial = this.diffuserMaterial
    this.glowMaterial = new THREE.MeshBasicMaterial({
      map: createGlowTexture(),
      transparent: true,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
      opacity: 0,
    })
    const glowMaterial = this.glowMaterial
    const housingGeometry = new THREE.BoxGeometry(
      tileX * 0.98,
      0.07,
      tileZ * 0.98,
    )
    const diffuserGeometry = new THREE.PlaneGeometry(tileX * 0.88, tileZ * 0.92)
    const glowGeometry = new THREE.PlaneGeometry(3.6, 3.6)
    const housingPlacements: THREE.Matrix4[] = []
    const diffuserPlacements: THREE.Matrix4[] = []
    for (let column = 1; column < columns; column += 3) {
      const x = -width / 2 + (column + 0.5) * tileX
      for (let row = 1; row < rows; row += 2) {
        const z = -depth / 2 + (row + 0.5) * tileZ
        housingPlacements.push(new THREE.Matrix4().makeTranslation(x, 3.168, z))
        diffuserPlacements.push(
          new THREE.Matrix4()
            .makeRotationX(Math.PI / 2)
            .setPosition(x, 3.131, z),
        )

        const glow = new THREE.Mesh(glowGeometry, glowMaterial)
        glow.position.set(x, 0.02, z)
        glow.rotation.x = -Math.PI / 2
        glow.matrixAutoUpdate = false
        glow.updateMatrix()
        this.scene.add(glow)
        this.laneGlows.push(glow)
      }
    }
    const lampRows = Math.max(1, Math.round(depth / 3.6))
    for (let aisle = 0; aisle <= unitCount; aisle++) {
      for (let row = 0; row < lampRows; row++) {
        this.lampAnchors.push(
          new THREE.Vector3(
            (aisle - unitCount / 2) * 2,
            2.85,
            -depth / 2 + (depth / lampRows) * (row + 0.5),
          ),
        )
      }
    }
    this.buildInstanced(housingGeometry, housingMaterial, housingPlacements)
    this.buildInstanced(diffuserGeometry, diffuserMaterial, diffuserPlacements)

    const woodMaterial = WoodNodeMaterial.fromPreset("maple", "matte")
    woodMaterial.transformationMatrix.makeScale(4, 4, 4)
    const runs: ShelfRun[] = []
    const spinePlacements: THREE.Matrix4[] = []
    const basePlacements: THREE.Matrix4[] = []
    const boardPlacements: THREE.Matrix4[] = []

    this.shelfStart = -0.5 - gondolaLength / 2
    this.shelfEnd = -0.5 + gondolaLength / 2
    for (let unit = 0; unit < unitCount; unit++) {
      const x = (unit - (unitCount - 1) / 2) * 2
      const zStart = -0.5 - gondolaLength / 2

      spinePlacements.push(new THREE.Matrix4().makeTranslation(x, 1.025, -0.5))
      basePlacements.push(new THREE.Matrix4().makeTranslation(x, 0.14, -0.5))

      const margin = (gondolaLength - perLevel * slotWidth) / 2
      for (const side of [-1, 1]) {
        const rows: Slot[][] = []
        for (const level of levels) {
          boardPlacements.push(
            new THREE.Matrix4().makeTranslation(
              x + side * 0.0675,
              level - 0.015,
              -0.5,
            ),
          )

          const row: Slot[] = []
          for (let index = 0; index < perLevel; index++) {
            row.push({
              position: new THREE.Vector3(
                x + side * 0.0796,
                level + 0.092,
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
          aisle: side < 0 ? unit : unit + 1,
          side: side < 0 ? "right" : "left",
        })
      }

      this.colliders.push(
        new THREE.Box3(
          new THREE.Vector3(x - 0.22, 0, zStart - 0.1),
          new THREE.Vector3(x + 0.22, 2.1, zStart + gondolaLength + 0.1),
        ),
      )
    }

    this.shelves.push(
      this.buildInstanced(
        new THREE.BoxGeometry(0.08, 2.05, gondolaLength),
        woodMaterial,
        spinePlacements,
      ),
      this.buildInstanced(
        new THREE.BoxGeometry(0.35, 0.28, gondolaLength),
        woodMaterial,
        basePlacements,
      ),
      this.buildInstanced(
        new THREE.BoxGeometry(0.135, 0.03, gondolaLength),
        woodMaterial,
        boardPlacements,
      ),
    )

    // TODO: Validate
    const hangPoster = (
      along: number,
      spacing: number,
      place: (offset: number, size: number) => THREE.Vector3,
      turn: number,
    ) => {
      const size = Math.min(1.2, spacing - 0.14)
      const poster = new THREE.Mesh(
        new THREE.PlaneGeometry(size, size * 1.5),
        new THREE.MeshStandardMaterial({ color: 0x1b1b22, roughness: 0.6 }),
      )
      poster.position.copy(place(along, size))
      poster.rotation.y = turn
      poster.matrixAutoUpdate = false
      poster.updateMatrix()
      this.scene.add(poster)
      this.posters.push(poster)
    }

    const backCount = Math.max(3, Math.floor(width / 1.45))
    const backSpacing = width / backCount
    for (let index = 0; index < backCount; index++) {
      hangPoster(
        index,
        backSpacing,
        (offset) =>
          new THREE.Vector3(
            -width / 2 + backSpacing * (offset + 0.5),
            1.75,
            -depth / 2 + 0.07,
          ),
        0,
      )
    }

    const sideCount = Math.max(2, Math.floor(depth / 1.45))
    const sideSpacing = depth / sideCount
    for (let index = 0; index < sideCount; index++) {
      const z = -depth / 2 + sideSpacing * (index + 0.5)
      hangPoster(
        index,
        sideSpacing,
        () => new THREE.Vector3(-width / 2 + 0.07, 1.75, z),
        Math.PI / 2,
      )
      hangPoster(
        index,
        sideSpacing,
        () => new THREE.Vector3(width / 2 - 0.07, 1.75, z),
        -Math.PI / 2,
      )
    }

    this.roomMaterials.push(wallMaterial)
    const counter = new THREE.Mesh(
      new THREE.BoxGeometry(2.6, 1.05, 0.7),
      woodMaterial,
    )
    counter.position.set(width / 2 - 1.8, 0.525, depth / 2 - 1.95)
    counter.userData = { toggle: "filters" }
    this.swatches.push(counter)
    this.counterTop.set(width / 2 - 1.8, 1.09, depth / 2 - 2.27)
    this.scene.add(counter)

    const board = new THREE.Mesh(
      new THREE.PlaneGeometry(2.6, 0.7),
      new THREE.MeshBasicMaterial({ map: createFilterBoardTexture([], []) }),
    )
    board.position.set(width / 2 - 1.8, 1.056, depth / 2 - 1.95)
    board.rotation.x = -Math.PI / 2
    board.matrixAutoUpdate = false
    board.updateMatrix()
    const sign = new THREE.Mesh(
      new THREE.PlaneGeometry(3.2, 0.8),
      new THREE.MeshBasicMaterial({
        map: createStoreSignTexture(storeName),
        toneMapped: false,
      }),
    )
    sign.position.set(width / 2 - 1.8, 2.8, depth / 2 - 0.09)
    sign.rotation.y = Math.PI
    sign.matrixAutoUpdate = false
    sign.updateMatrix()
    this.scene.add(sign)
    this.storeSigns.push(sign)

    const streetSign = new THREE.Mesh(
      new THREE.PlaneGeometry(3.2, 0.8),
      new THREE.MeshBasicMaterial({
        map: createStoreSignTexture(storeName),
        toneMapped: false,
      }),
    )
    streetSign.position.set(doorCenter, 2.8, depth / 2 + 0.09)
    streetSign.matrixAutoUpdate = false
    streetSign.updateMatrix()
    this.scene.add(streetSign)
    this.storeSigns.push(streetSign)

    for (const level of [0.9, 1.22, 1.54]) {
      const holdBoard = new THREE.Mesh(
        new THREE.BoxGeometry(2.6, 0.03, 0.135),
        woodMaterial,
      )
      holdBoard.position.set(width / 2 - 1.8, level, depth / 2 - 0.12)
      this.scene.add(holdBoard)
      this.counterRows.push(
        new THREE.Vector3(
          width / 2 - 1.8 + 1.3 - slotWidth / 2,
          level + 0.107,
          depth / 2 - 0.12,
        ),
      )
    }
    this.counterStep = slotWidth
    this.counterCapacity = Math.max(1, Math.floor(2.6 / slotWidth))

    const deskButtons = [
      ["create-channel", "Create channel"],
      ["counter-covers", "Load covers"],
      ["add-channel", "Add to channel"],
    ]
    const buttonGeometry = new THREE.PlaneGeometry(0.62, 0.194)
    for (const [index, [toggle, label]] of deskButtons.entries()) {
      const buttonMaterial = new THREE.MeshBasicMaterial({
        map: createLabelTexture(label),
      })
      for (const [side, z, turn] of [
        [-1, depth / 2 - 2.306, Math.PI],
        [1, depth / 2 - 1.594, 0],
      ] as const) {
        const button = new THREE.Mesh(buttonGeometry, buttonMaterial)
        button.position.set(
          width / 2 - 1.8 - side * (index - 1) * 0.85,
          0.72,
          z,
        )
        button.rotation.y = turn
        button.userData = { toggle }
        button.matrixAutoUpdate = false
        button.updateMatrix()
        this.scene.add(button)
        this.swatches.push(button)
        if (toggle !== "counter-covers") {
          button.visible = false
          button.layers.disableAll()
          this.channelButtons.push(button)
        }
      }
    }

    board.userData = { toggle: "filters" }
    this.scene.add(board)
    this.swatches.push(board)
    this.filterBoard = board

    this.colliders.push(new THREE.Box3().setFromObject(counter))

    const signGeometry = new THREE.PlaneGeometry(1.8, 0.45)
    for (let aisle = 0; aisle <= unitCount; aisle++) {
      const signX = (aisle - unitCount / 2) * 2
      const near = new THREE.Mesh(signGeometry, new THREE.MeshBasicMaterial())
      near.position.set(signX, 2.46, -0.5 + gondolaLength / 2 + 0.22)
      const far = new THREE.Mesh(signGeometry, new THREE.MeshBasicMaterial())
      far.position.set(signX, 2.46, -0.5 - gondolaLength / 2 - 0.22)
      far.rotation.y = Math.PI
      const nearBack = new THREE.Mesh(signGeometry, far.material)
      nearBack.position.copy(near.position)
      nearBack.rotation.y = Math.PI
      const farBack = new THREE.Mesh(signGeometry, near.material)
      farBack.position.copy(far.position)
      const group = new THREE.Group()
      group.visible = false
      for (const face of [near, far, nearBack, farBack]) {
        face.matrixAutoUpdate = false
        face.updateMatrix()
        group.add(face)
      }
      this.scene.add(group)
      this.aisleSigns.push({
        left: [],
        right: [],
        near,
        far,
        group,
        anchor: new THREE.Vector3(signX, 2.46, -0.5),
        dirty: true,
      })
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

    this.runMeshes = runs.map(() => [])
    this.runTitles = runs.map(() => [])
    this.runSlots = runs.map(() => [])
    this.blockPlacements = runs.map(() => [])
    this.runCenters = runs.map((run) => {
      const row = run.levels[Math.floor(run.levels.length / 2)]
      return row[0].position.clone().lerp(row[row.length - 1].position, 0.5)
    })
    this.runGroups = runs.map(() => {
      const group = new THREE.Group()
      group.visible = false
      group.matrixAutoUpdate = false
      this.scene.add(group)
      return group
    })
    this.caseGroups = this.runGroups.map((parent) => {
      const group = new THREE.Group()
      group.visible = false
      group.matrixAutoUpdate = false
      parent.add(group)
      return group
    })

    const loaderGeometry = new THREE.PlaneGeometry(0.62, 0.194)
    for (let index = 0; index < runs.length; index++) {
      const slot = runs[index].order[0]
      const button = new THREE.Mesh(loaderGeometry, this.loadCoversMaterial)
      button.rotation.y = Math.atan2(slot.facing.x, slot.facing.z)
      button.userData = { run: index }
      button.matrixAutoUpdate = false
      button.visible = false
      this.scene.add(button)
      this.loaderButtons.push(button)
      this.placeLoaderButton(index)
    }

    this.blocks = this.buildInstanced(
      new THREE.BoxGeometry(1, 1, 1),
      this.blockMaterial,
      [],
      runs.length * levels.length,
    )
  }

  // TODO: Validate
  private buildInstanced(
    geometry: THREE.BufferGeometry,
    material: THREE.Material,
    placements: THREE.Matrix4[],
    count = placements.length,
  ) {
    const mesh = new THREE.InstancedMesh(geometry, material, count)
    for (const [index, placement] of placements.entries()) {
      mesh.setMatrixAt(index, placement)
    }
    for (let index = placements.length; index < count; index++) {
      mesh.setMatrixAt(index, new THREE.Matrix4().makeScale(0, 0, 0))
    }
    mesh.instanceMatrix.needsUpdate = true
    mesh.frustumCulled = false
    mesh.matrixAutoUpdate = false
    this.instanced.push(mesh)
    this.scene.add(mesh)
    return mesh
  }

  // TODO: Validate
  private refreshBlocks() {
    for (let index = 0; index < this.runs.length; index++) {
      const run = this.runs[index]
      const filled = this.runTitles[index].length
      const placements: THREE.Matrix4[] = []
      if (filled > 0) {
        const columns = Math.min(
          run.levels[0].length,
          Math.ceil(filled / run.levels.length),
        )
        const along = run.levels[0][0].facing.x !== 0 ? "z" : "x"
        for (const row of run.levels) {
          const near = row[row.length - 1].position
          const far = row[row.length - columns].position
          const span = Math.abs(near[along] - far[along]) + 0.172
          placements.push(
            new THREE.Matrix4()
              .makeScale(
                along === "z" ? 0.02 : span,
                0.19,
                along === "z" ? span : 0.02,
              )
              .setPosition(this.scratch.copy(near).lerp(far, 0.5)),
          )
        }
      }
      this.blockPlacements[index] = placements
    }
    this.applyBlocks()
  }

  // TODO: Validate
  private applyBlocks() {
    if (!this.blocks) return
    const levels = this.runs[0]?.levels.length ?? 0
    const hidden = new THREE.Matrix4().makeScale(0, 0, 0)
    for (let index = 0; index < this.runs.length; index++) {
      const shown = this.visibleRuns.has(index) && !this.nearRuns.has(index)
      const placements = this.blockPlacements[index]
      for (let level = 0; level < levels; level++) {
        this.blocks.setMatrixAt(
          index * levels + level,
          shown && placements[level] ? placements[level] : hidden,
        )
      }
    }
    this.blocks.instanceMatrix.needsUpdate = true
  }

  // TODO: Validate
  private updateLod() {
    let changed = false
    for (let index = 0; index < this.runs.length; index++) {
      const distance = this.runCenters[index].distanceTo(this.camera.position)
      const near = this.nearRuns.has(index)
      if (near ? distance < 17 : distance < 14) {
        if (!near) {
          this.nearRuns.add(index)
          changed = true
        }
      } else if (near) {
        this.nearRuns.delete(index)
        changed = true
      }

      const shown = this.visibleRuns.has(index)
      if (distance < (shown ? this.viewRange * 1.15 : this.viewRange)) {
        if (!shown) {
          this.visibleRuns.add(index)
          changed = true
        }
      } else if (shown) {
        this.visibleRuns.delete(index)
        changed = true
      }
    }
    this.updateSigns()
    this.updatePosters()
    if (changed) this.applyLod()
  }

  // TODO: Validate
  private updateSigns() {
    for (const [index, sign] of this.aisleSigns.entries()) {
      const distance = sign.anchor.distanceTo(this.camera.position)
      const shown = this.visibleSigns.has(index)
      if (distance < (shown ? this.viewRange * 1.15 : this.viewRange)) {
        if (shown) continue
        this.visibleSigns.add(index)
        if (sign.dirty) this.refreshSign(sign)
        sign.group.visible = true
        continue
      }
      if (!shown) continue
      this.visibleSigns.delete(index)
      sign.group.visible = false
      this.clearSign(sign)
    }
  }

  // TODO: Validate
  private clearSign(sign: AisleSign) {
    for (const face of [sign.near, sign.far]) {
      const material = face.material as THREE.MeshBasicMaterial
      material.map?.dispose()
      material.map = null
      material.needsUpdate = true
    }
    sign.dirty = true
  }

  // TODO: Validate
  private updatePosters() {
    for (const poster of this.posters) {
      const shown =
        poster.position.distanceTo(this.camera.position) < this.viewRange
      poster.visible = shown
      if (!shown || poster.userData.painted) continue
      const title = poster.userData.title as StoreTitle | undefined
      if (!title) continue
      poster.userData.painted = true
      this.paintPoster(poster, title)
    }
  }

  // TODO: Validate
  private moveLights() {
    this.forest?.setCameraPosition(this.camera.position)
    if (this.lampPool.length === 0) return
    const kept = this.lampPool.length + 1
    const chosen: number[] = []
    const ranges: number[] = []
    for (const [index, anchor] of this.lampAnchors.entries()) {
      const range = anchor.distanceToSquared(this.camera.position)
      if (chosen.length === kept && range >= ranges[ranges.length - 1]) {
        continue
      }
      let slot = chosen.length
      while (slot > 0 && ranges[slot - 1] > range) slot--
      chosen.splice(slot, 0, index)
      ranges.splice(slot, 0, range)
      if (chosen.length > kept) {
        chosen.pop()
        ranges.pop()
      }
    }
    const edge = Math.sqrt(
      ranges[this.lampPool.length] ?? Number.POSITIVE_INFINITY,
    )
    for (const [slot, bulb] of this.lampPool.entries()) {
      bulb.position.copy(this.lampAnchors[chosen[slot] ?? 0])
      const margin = (edge - Math.sqrt(ranges[slot] ?? edge)) / (edge * 0.35)
      const fade = Number.isFinite(edge) ? Math.min(Math.max(margin, 0), 1) : 1
      bulb.intensity = 1.3 * this.lightLevel * fade * fade * (3 - 2 * fade)
    }
  }

  // TODO: Validate
  private applyLod() {
    for (let index = 0; index < this.runs.length; index++) {
      const near = this.visibleRuns.has(index) && this.nearRuns.has(index)
      if (near) this.mountRun(index)
      else this.unmountRun(index)
    }
    this.cullRuns()
    this.applyBlocks()
  }

  // TODO: Validate
  private cullRuns() {
    const camera = this.camera.position
    const betweenShelves =
      camera.z > this.shelfStart && camera.z < this.shelfEnd
    for (let index = 0; index < this.runs.length; index++) {
      const run = this.runs[index]
      const slot = run.order[0]
      const ahead = (camera.x - slot.position.x) * slot.facing.x
      const outerAisle = run.aisle === 0 || run.aisle === this.runs.length / 2
      const seen = ahead > 0 && (!betweenShelves || outerAisle || ahead < 2)
      const shown = this.visibleRuns.has(index) && seen
      this.runGroups[index].visible = shown
      this.caseGroups[index].visible = shown && this.nearRuns.has(index)
      this.loaderButtons[index].visible = shown
    }
  }

  // TODO: Validate
  private mountRun(index: number) {
    if (this.mountedRuns.has(index)) return
    this.mountedRuns.add(index)
    const run = this.runs[index]
    const titles = this.runTitles[index]
    const group = this.caseGroups[index]
    const meshes: THREE.Mesh[] = []
    const slots = this.runSlots[index]
    for (const [offset, title] of titles.entries()) {
      const mesh = this.takeCase(title)
      group.add(mesh)
      this.settleCase(mesh, run.order[slots[offset]])
      meshes.push(mesh)
    }
    this.runMeshes[index] = meshes
    if (!this.revealedRuns.has(index)) {
      this.batchRun(index)
      return
    }
    for (const mesh of meshes) this.queueImage(mesh)
    for (let concurrent = 0; concurrent < 6; concurrent++) this.nextImage()
  }

  // TODO: Validate
  private unmountRun(index: number) {
    if (!this.mountedRuns.has(index)) return
    this.unbatchRun(index)
    this.mountedRuns.delete(index)
    const meshes = this.runMeshes[index]
    this.runMeshes[index] = []
    const group = this.caseGroups[index]
    for (const mesh of meshes) {
      group.remove(mesh)
      this.releaseCase(mesh)
    }
  }

  // TODO: Validate
  private batchRun(index: number) {
    const meshes = this.runMeshes[index]
    if (meshes.length === 0) return
    const batch = new THREE.InstancedMesh(
      this.caseGeometry,
      this.batchMaterial,
      meshes.length,
    )
    batch.matrixAutoUpdate = false
    for (const [slot, mesh] of meshes.entries()) {
      mesh.userData.batch = batch
      mesh.userData.batchSlot = slot
      batch.setColorAt(
        slot,
        this.placeholderMaterial(mesh.userData.title as StoreTitle).color,
      )
      this.batchCase(mesh, mesh === this.focused)
    }
    batch.computeBoundingSphere()
    this.caseGroups[index].add(batch)
    this.runBatches.set(index, batch)
  }

  // TODO: Validate
  private unbatchRun(index: number) {
    const batch = this.runBatches.get(index)
    if (!batch) return
    this.runBatches.delete(index)
    batch.removeFromParent()
    batch.dispose()
    for (const mesh of this.runMeshes[index]) {
      mesh.visible = true
      delete mesh.userData.batch
      delete mesh.userData.batchSlot
    }
  }

  // TODO: Validate
  private batchCase(mesh: THREE.Mesh, shown: boolean) {
    const batch = mesh.userData.batch as THREE.InstancedMesh | undefined
    if (!batch) return
    mesh.visible = shown
    batch.setMatrixAt(
      mesh.userData.batchSlot as number,
      shown ? this.hiddenInstance : mesh.matrix,
    )
    batch.instanceMatrix.needsUpdate = true
  }

  // TODO: Validate
  private mountedCases() {
    const meshes: THREE.Mesh[] = []
    for (const index of this.mountedRuns) meshes.push(...this.runMeshes[index])
    return meshes
  }

  // TODO: Validate
  private takeCase(title: StoreTitle) {
    let mesh = this.casePool.pop()
    if (!mesh) {
      mesh = new THREE.Mesh(this.caseGeometry)
      mesh.matrixAutoUpdate = false
      mesh.rotation.order = "YXZ"
    }
    mesh.geometry = this.caseGeometry
    mesh.scale.setScalar(this.caseScale)
    mesh.material = this.placeholderMaterial(title)
    mesh.visible = true
    mesh.userData = {
      title,
      generation: ++this.generationCounter,
      basePosition: new THREE.Vector3(),
      facing: new THREE.Vector3(0, 0, 1),
      spin: seededOffset(`${title.id}-spin`),
      drift: seededOffset(`${title.id}-drift`),
    }
    return mesh
  }

  // TODO: Validate
  private releaseCase(mesh: THREE.Mesh) {
    if (mesh === this.focused) this.applyFocus(null)
    this.clearCover(mesh)
    mesh.userData = {}
    this.casePool.push(mesh)
  }

  // TODO: Validate
  private clearCover(mesh: THREE.Mesh) {
    this.pendingImages = this.pendingImages.filter(
      (entry) => entry.mesh !== mesh,
    )
    this.reportCovers()
    const material = mesh.userData.material as
      | THREE.MeshStandardMaterial
      | THREE.MeshBasicMaterial
      | undefined
    const shared = this.counterCases.some((held) => held.material === material)
    if (material && !shared) {
      this.caseMaterials.delete(material)
      material.map?.dispose()
      material.dispose()
    }
    mesh.userData.generation = ++this.generationCounter
    delete mesh.userData.imageQueued
    delete mesh.userData.material
    delete mesh.userData.texture
  }

  // TODO: Validate
  private refreshSign(sign: AisleSign) {
    sign.dirty = false
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
  setShelfGenres(genres: string[] | null) {
    this.shelfFilter = genres === null ? null : new Set(genres)
  }

  // TODO: Validate
  restock(titles: StoreTitle[]) {
    this.allTitles = []
    this.genreTitles.clear()
    this.placedTitles = 0
    this.restocked = true
    this.addTitles(titles)
  }

  // TODO: Validate
  addTitles(titles: StoreTitle[]) {
    let added = this.restocked
    this.restocked = false
    for (let index = this.placedTitles; index < titles.length; index++) {
      const title = titles[index]
      this.allTitles.push(title)
      const genreNames = shelfGenres(title, this.shelfFilter)
      if (genreNames.length === 0 && title.genres.length > 0) continue
      for (const genre of genreNames.length ? genreNames : ["Unknown"]) {
        const shelved = this.genreTitles.get(genre) ?? []
        shelved.push(title)
        this.genreTitles.set(genre, shelved)
        added = true
      }
    }
    this.placedTitles = titles.length

    if (added) {
      this.layoutStore()
      this.dressPosters()
      this.refreshBlocks()
      this.updateLod()
      this.applyLod()
      this.moveLights()
    }
    for (let concurrent = 0; concurrent < 6; concurrent++) this.nextImage()
  }

  // TODO: Validate
  private genreOrder() {
    const named = [...this.genreTitles.keys()]
      .filter((genre) => genre !== "Unknown")
      .sort((left, right) => right.localeCompare(left))
    return this.genreTitles.has("Unknown") ? [...named, "Unknown"] : named
  }

  // TODO: Validate
  private layoutStore() {
    for (const index of [...this.mountedRuns]) this.unmountRun(index)
    this.runTitles = this.runs.map(() => [])
    this.runSlots = this.runs.map(() => [])
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
      const shelved = this.genreTitles.get(genre) ?? []
      if (genre === "Unknown" && cursor > 0) {
        slot = this.aisleStarts.find((start) => start > slot) ?? slot + 1
        cursor = 0
      }
      if (cursor > 0 && slot < this.packOrder.length) {
        const levels = this.runs[this.packOrder[slot]].levels.length
        cursor = Math.ceil(cursor / levels) * levels
      }
      for (const title of shelved) {
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
          this.settleTag(tags, genre, run.order[cursor], runIndex)
          tags++
          sections.push({ run: runIndex, start: cursor, end: cursor, genre })
        }
        sections[sections.length - 1].end = cursor
        this.runTitles[runIndex].push(title)
        this.runSlots[runIndex].push(cursor)
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
          section.run,
        )
        strips++
      }
    }
    for (let index = strips; index < this.stripPool.length; index++) {
      this.stripPool[index].visible = false
    }
  }

  // TODO: Validate
  private settleStrip(
    index: number,
    genre: string,
    near: Slot,
    far: Slot,
    runIndex: number,
  ) {
    let mesh = this.stripPool[index]
    if (!mesh) {
      mesh = new THREE.Mesh(this.stripGeometry, this.stripMaterial(genre))
      mesh.matrixAutoUpdate = false
      this.stripPool.push(mesh)
    }
    this.runGroups[runIndex].add(mesh)
    mesh.material = this.stripMaterial(genre)
    mesh.visible = true
    mesh.scale.z = Math.abs(near.position.z - far.position.z) + 0.172
    mesh.position
      .copy(near.position)
      .addScaledVector(near.facing, 0.056)
      .setY(near.position.y - 0.104)
      .setZ((near.position.z + far.position.z) / 2)
    mesh.updateMatrix()
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
      const listed = [...entries[runIndex]].reverse()
      if (run.side === "left") sign.left = listed
      else sign.right = listed
    }
    for (const [index, sign] of this.aisleSigns.entries()) {
      sign.dirty = true
      if (this.visibleSigns.has(index)) this.refreshSign(sign)
    }
  }

  // TODO: Validate
  private settleTag(
    index: number,
    genre: string,
    slot: Slot,
    runIndex: number,
  ) {
    let mesh = this.tagPool[index]
    if (!mesh) {
      mesh = new THREE.Mesh(this.tagGeometry, this.tagMaterial(genre))
      mesh.matrixAutoUpdate = false
      this.tagPool.push(mesh)
    }
    this.runGroups[runIndex].add(mesh)
    mesh.material = this.tagMaterial(genre)
    mesh.visible = true
    mesh.position
      .copy(slot.position)
      .addScaledVector(slot.facing, 0.056)
      .setY(slot.position.y - 0.117)
    mesh.rotation.y = Math.atan2(slot.facing.x, slot.facing.z)
    mesh.updateMatrix()
  }

  // TODO: Validate
  private tagMaterial(genre: string) {
    let material = this.tagMaterials.get(genre)
    if (!material) {
      material = new THREE.MeshBasicMaterial({ map: createTagTexture(genre) })
      this.tagMaterials.set(genre, material)
    }
    return material
  }

  // TODO: Validate
  private dressPosters() {
    const seen = new Set<string>()
    const candidates: StoreTitle[] = []
    for (const title of this.allTitles) {
      if (!title.imageUrl || seen.has(title.id)) continue
      seen.add(title.id)
      candidates.push(title)
    }
    if (candidates.length === 0) return

    candidates.sort(
      (left, right) =>
        (right.tmdbPopularity ?? -1) - (left.tmdbPopularity ?? -1),
    )
    const picks = candidates.slice(
      0,
      Math.max(Math.ceil(candidates.length * 0.1), this.posters.length),
    )
    for (let index = picks.length - 1; index > 0; index--) {
      const swap = Math.floor(Math.random() * (index + 1))
      ;[picks[index], picks[swap]] = [picks[swap], picks[index]]
    }

    for (const [index, poster] of this.posters.entries()) {
      const title = picks[index % picks.length]
      if (!title || poster.userData.title === title) continue
      poster.userData = {
        title,
        painted: false,
        basePosition: poster.position.clone(),
        facing: new THREE.Vector3(
          Math.sin(poster.rotation.y),
          0,
          Math.cos(poster.rotation.y),
        ),
        material: poster.material,
      }
    }
    this.updatePosters()
  }

  // TODO: Validate
  private async paintPoster(poster: THREE.Mesh, title: StoreTitle) {
    const full = this.fullPosters
    let source = title.imageUrl
    let isPoster = title.isPoster
    if (full) {
      const detail = await fetchTitleDetail(title.id, this.metadata)
      if (this.disposed) return
      const posterUrl =
        detail.poster_url ?? (title.isPoster ? title.imageUrl : null)
      source = posterUrl ?? detail.image_url ?? title.imageUrl
      isPoster = Boolean(posterUrl)
    }
    if (!source) return
    // TODO: Validate
    const finish = (loaded: HTMLImageElement | null) => {
      if (this.disposed || !loaded || full !== this.fullPosters) return
      const canvas = createCaseCanvas({ ...title, isPoster }, loaded, 3)
      const texture = new THREE.CanvasTexture(canvas)
      texture.colorSpace = THREE.SRGBColorSpace
      texture.anisotropy = 4
      texture.offset.set(0, 32 / 256)
      texture.repeat.set(168 / 256, 224 / 256)
      const material = poster.material as THREE.MeshStandardMaterial
      material.map?.dispose()
      material.map = texture
      material.color.set(0xffffff)
      material.needsUpdate = true
    }
    finish(await loadStoreImage(source))
  }

  // TODO: Validate
  private trigger(mesh: THREE.Mesh) {
    if (mesh.userData.toggle === "filters") {
      if (!this.touch) this.exit()
      this.callbacks.onFilters()
      return
    }
    if (mesh.userData.toggle === "door") {
      const leaf = this.doorLeaves[mesh.userData.leaf as number]
      leaf.open = !leaf.open
      return
    }
    if (mesh.userData.toggle === "counter-covers") {
      for (const held of this.counterCases) this.queueImage(held)
      for (let concurrent = 0; concurrent < 6; concurrent++) this.nextImage()
      return
    }
    if (mesh.userData.toggle === "create-channel") {
      if (!this.touch) this.exit()
      this.callbacks.onChannelAction("create")
      return
    }
    if (mesh.userData.toggle === "add-channel") {
      if (!this.touch) this.exit()
      this.callbacks.onChannelAction("add")
      return
    }
    const runIndex = mesh.userData.run as number
    if (this.revealedRuns.has(runIndex)) this.conceal(runIndex)
    else this.reveal(runIndex)
  }

  // TODO: Validate
  private placeLoaderButton(runIndex: number) {
    const slot = this.runs[runIndex].order[0]
    const revealed = this.revealedRuns.has(runIndex)
    const button = this.loaderButtons[runIndex]
    button.position
      .copy(slot.position)
      .addScaledVector(slot.facing, revealed ? 0.1 : 0.42)
      .setY(revealed ? 0.14 : 1.58)
    button.updateMatrix()
  }

  // TODO: Validate
  private reveal(runIndex: number) {
    this.revealedRuns.add(runIndex)
    this.loaderButtons[runIndex].material = this.unloadCoversMaterial
    this.placeLoaderButton(runIndex)
    this.unbatchRun(runIndex)
    for (const mesh of this.runMeshes[runIndex]) this.queueImage(mesh)
    for (let concurrent = 0; concurrent < 6; concurrent++) this.nextImage()
  }

  // TODO: Validate
  private conceal(runIndex: number) {
    this.revealedRuns.delete(runIndex)
    this.loaderButtons[runIndex].material = this.loadCoversMaterial
    this.placeLoaderButton(runIndex)
    for (const mesh of this.runMeshes[runIndex]) {
      this.clearCover(mesh)
      const placeholder = this.placeholderMaterial(
        mesh.userData.title as StoreTitle,
      )
      if (mesh === this.focused) this.dressHighlight(mesh)
      else mesh.material = placeholder
    }
    if (this.mountedRuns.has(runIndex)) this.batchRun(runIndex)
  }

  // TODO: Validate
  private settleCase(mesh: THREE.Mesh, slot: Slot) {
    const strength = this.askew * this.askew
    const spin = mesh.userData.spin as THREE.Vector3
    const drift = mesh.userData.drift as THREE.Vector3
    mesh.userData.slot = slot.position.clone()
    mesh.userData.basePosition = slot.position
      .clone()
      .setY(slot.position.y + 0.092 * (this.caseScale - 1))
      .addScaledVector(drift, 0.06 * strength)
    mesh.userData.facing = slot.facing.clone()
    mesh.position.copy(mesh.userData.basePosition as THREE.Vector3)
    if (mesh === this.focused) {
      mesh.position.addScaledVector(slot.facing, 0.04)
    }
    mesh.rotation.x = -0.349 + spin.x * 0.6 * strength
    mesh.rotation.y =
      Math.atan2(slot.facing.x, slot.facing.z) + spin.y * 0.6 * strength
    mesh.rotation.z = spin.z * 0.6 * strength
    mesh.updateMatrix()
    this.batchCase(mesh, mesh.visible)
  }

  // TODO: Validate
  private trackCase<
    T extends THREE.MeshStandardMaterial | THREE.MeshBasicMaterial,
  >(material: T) {
    if (material instanceof THREE.MeshStandardMaterial) {
      material.userData.roughness = material.roughness
      material.userData.metalness = material.metalness
      if (!this.reflections) {
        material.roughness = 1
        material.metalness = 0
      }
    }
    this.caseMaterials.add(material)
    return material
  }

  // TODO: Validate
  isVhs() {
    return this.format === 1
  }

  // TODO: Validate
  private seedDrop(streaks: Float32Array, offset: number, top: number) {
    const x = (Math.random() - 0.5) * this.rainSpanX
    const z = (Math.random() - 0.5) * this.rainSpanZ + this.rainCenterZ
    streaks[offset] = x
    streaks[offset + 1] = top
    streaks[offset + 2] = z
    streaks[offset + 3] = x
    streaks[offset + 4] = top - 0.7
    streaks[offset + 5] = z
  }

  // TODO: Validate
  setRain(drops: number, speed: number) {
    this.rainSpeed = speed
    this.rain?.geometry.setDrawRange(0, Math.round(drops) * 2)
  }

  // TODO: Validate
  private fallRain(delta: number) {
    if (!this.rain) return
    const falling = this.rain.geometry.drawRange.count / 2
    this.rain.visible = falling > 0
    if (!this.rain.visible) return

    const attribute = this.rain.geometry.getAttribute(
      "position",
    ) as THREE.BufferAttribute
    const streaks = attribute.array as Float32Array
    const drop = this.rainSpeed * delta
    for (let index = 0; index < falling; index++) {
      const offset = index * 6
      streaks[offset + 1] -= drop
      streaks[offset + 4] -= drop
      const sheltered =
        Math.abs(streaks[offset]) < this.rainRoofX &&
        streaks[offset + 2] < this.rainRoofZ
      if (streaks[offset + 4] > (sheltered ? 3.3 : 0)) continue
      this.splash(streaks[offset], sheltered ? 3.3 : 0, streaks[offset + 2])
      this.seedDrop(streaks, offset, 26)
    }
    attribute.needsUpdate = true
    this.spreadSplashes(delta)
  }

  // TODO: Validate
  private splash(x: number, y: number, z: number) {
    const ripple = this.ripples[this.rippleCursor]
    this.rippleCursor = (this.rippleCursor + 1) % this.ripples.length
    ripple.x = x
    ripple.y = y
    ripple.z = z
    ripple.age = 0
  }

  // TODO: Validate
  private spreadSplashes(delta: number) {
    if (!this.splashes) return
    const placement = new THREE.Matrix4()
    const fade = new THREE.Color()
    let shown = 0
    for (const ripple of this.ripples) {
      if (ripple.age >= 1) continue
      ripple.age = Math.min(1, ripple.age + delta * 2.6)
      const spread = 0.12 + ripple.age * 0.75
      placement.makeScale(spread, 1, spread)
      placement.setPosition(ripple.x, ripple.y + 0.02, ripple.z)
      this.splashes.setMatrixAt(shown, placement)
      fade.setScalar((1 - ripple.age) * 0.7)
      this.splashes.setColorAt(shown, fade)
      shown++
    }
    this.splashes.count = shown
    this.splashes.instanceMatrix.needsUpdate = true
    if (this.splashes.instanceColor) {
      this.splashes.instanceColor.needsUpdate = true
    }
  }

  // TODO: Validate
  private levelTerrain(
    terrain: TerrainGenerator,
    clearX: number,
    clearBack: number,
    clearFront: number,
    blend: number,
  ) {
    const { heights, gridSize: grid, geometry, minY: base } = terrain
    if (!heights || !grid || !geometry || base === undefined) return
    const segments = grid - 1
    const size = terrain.parameters.size
    const half = size / 2
    const cellSize = size / segments

    for (let indexZ = 0; indexZ < grid; indexZ++) {
      const worldZ = (indexZ / segments) * size - half
      const outsideZ = Math.max(clearBack - worldZ, worldZ - clearFront)
      for (let indexX = 0; indexX < grid; indexX++) {
        const worldX = (indexX / segments) * size - half
        const outsideX = Math.abs(worldX) - clearX
        const ramp = Math.min(
          1,
          Math.max(0, Math.max(outsideX, outsideZ)) / blend,
        )
        const offset = indexZ * grid + indexX
        heights[offset] =
          (heights[offset] - base) * ramp * ramp * (3 - 2 * ramp)
      }
    }

    const position = geometry.getAttribute("position")
    const normal = geometry.getAttribute("normal")
    let lowest = Infinity
    let highest = -Infinity
    for (let indexZ = 0; indexZ < grid; indexZ++) {
      const back = Math.max(0, indexZ - 1)
      const front = Math.min(grid - 1, indexZ + 1)
      for (let indexX = 0; indexX < grid; indexX++) {
        const offset = indexZ * grid + indexX
        const height = heights[offset]
        position.setY(offset, height)
        const left = Math.max(0, indexX - 1)
        const right = Math.min(grid - 1, indexX + 1)
        const slopeX =
          (heights[indexZ * grid + left] - heights[indexZ * grid + right]) /
          ((right - left) * cellSize)
        const slopeZ =
          (heights[back * grid + indexX] - heights[front * grid + indexX]) /
          ((front - back) * cellSize)
        const length = Math.hypot(slopeX, 1, slopeZ)
        normal.setXYZ(offset, slopeX / length, 1 / length, slopeZ / length)
        if (height < lowest) lowest = height
        if (height > highest) highest = height
      }
    }
    position.needsUpdate = true
    normal.needsUpdate = true
    geometry.computeBoundingSphere()
    terrain.minY = lowest
    terrain.maxY = highest
    terrain.minHeight.value = lowest
    terrain.maxHeight.value = highest
  }

  // TODO: Validate
  private unfog(group: THREE.Object3D) {
    group.traverse((object) => {
      const mesh = object as THREE.Mesh
      if (!mesh.isMesh) return
      const materials = Array.isArray(mesh.material)
        ? mesh.material
        : [mesh.material]
      for (const material of materials) {
        ;(material as THREE.Material & { fog: boolean }).fog = false
      }
    })
  }

  // TODO: Validate
  private dressOutdoors(group: THREE.Object3D) {
    group.traverse((object) => {
      const mesh = object as THREE.Mesh
      if (!mesh.isMesh) return
      const materials = Array.isArray(mesh.material)
        ? mesh.material
        : [mesh.material]
      for (const material of materials) {
        if (this.dressed.has(material)) continue
        this.dressed.add(material)
        const lit = material as THREE.MeshStandardMaterial & { fog: boolean }
        lit.fog = false
        lit.emissive?.setHex(0x000000)
      }
    })
  }

  // TODO: Validate
  private parkCars() {
    if (!this.cars || !this.litCars || this.parked.length === 0) return
    if (this.carFleet) this.scene.remove(this.carFleet)
    if (this.litFleet) this.scene.remove(this.litFleet)
    const strength = this.askew * this.askew
    const place = (car: (typeof this.parked)[number]) => ({
      color: car.color,
      matrix: new THREE.Matrix4()
        .makeRotationY(car.turn + car.spin.y * 0.5 * strength)
        .setPosition(
          car.x + car.drift.x * 1.6 * strength,
          -0.1,
          car.z + car.drift.z * 1.6 * strength,
        ),
    })

    this.carFleet = this.cars.build(
      this.parked.filter((car) => !car.lit).map(place),
    )
    for (const paint of this.cars.materials.values()) {
      ;(paint as { emissiveNode: unknown }).emissiveNode = null
    }
    this.dressOutdoors(this.carFleet)
    this.scene.add(this.carFleet)

    this.litFleet = this.litCars.build(
      this.parked.filter((car) => car.lit).map(place),
    )
    this.unfog(this.litFleet)
    this.scene.add(this.litFleet)
  }

  // TODO: Validate
  setOutdoorLights(level: number) {
    this.moonLight.intensity = level * 0.55
    this.skyLight.intensity = level * 0.5
    if (this.poolMaterial) this.poolMaterial.opacity = level * 0.25
  }

  // TODO: Validate
  setAskew(value: number) {
    this.askew = value / 50
    for (const mesh of [...this.mountedCases(), ...this.counterCases]) {
      const slot = mesh.userData.slot as THREE.Vector3 | undefined
      if (!slot) continue
      this.settleCase(mesh, {
        position: slot,
        facing: mesh.userData.facing as THREE.Vector3,
      })
    }
    for (const batch of this.runBatches.values()) batch.computeBoundingSphere()
    this.parkCars()
  }

  // TODO: Validate
  setFps(visible: boolean) {
    this.statsPanel.style.display = visible ? "flex" : "none"
  }

  // TODO: Validate
  setFullPosters(full: boolean) {
    if (full === this.fullPosters) return
    this.fullPosters = full
    for (const poster of this.posters) poster.userData.painted = false
    this.updatePosters()
  }

  // TODO: Validate
  setLampCount(count: number) {
    const target = Math.min(count, this.lampAnchors.length)
    while (this.lampPool.length < target) {
      const bulb = new THREE.PointLight(0xfff3e0, 1.3, 11, 2)
      this.lampPool.push(bulb)
      this.scene.add(bulb)
    }
    for (const bulb of this.lampPool.splice(target)) {
      this.scene.remove(bulb)
      bulb.dispose()
    }
    this.moveLights()
  }

  // TODO: Validate
  setLights(level: number) {
    const strength = level
    this.lightLevel = strength
    this.moveLights()
    if (this.glowMaterial) {
      this.glowMaterial.opacity = Math.min(strength, 1) * 0.16
    }
    this.diffuserMaterial?.color.setScalar(Math.min(strength, 1))
    this.ceilingMaterial?.emissive
      .setHex(0x4a4b52)
      .multiplyScalar(Math.min(strength, 1))
  }

  // TODO: Validate
  setFormat(format: number) {
    this.format = format
    const replacement =
      format === 1 ? buildCaseGeometry(0.105, 0.19, 0.028) : buildCaseGeometry()
    const previous = this.caseGeometry
    this.caseGeometry = replacement
    this.caseScale = format === 2 ? 0.168 / 0.135 : 1
    const lift = 0.092 * (this.caseScale - 1)
    for (const mesh of this.mountedCases()) {
      mesh.geometry = replacement
      mesh.scale.setScalar(this.caseScale)
      const slot = mesh.userData.slot as THREE.Vector3 | undefined
      if (slot) {
        const base = slot.clone().setY(slot.y + lift)
        mesh.userData.basePosition = base
        mesh.position.copy(base)
        if (mesh === this.focused) {
          mesh.position.addScaledVector(
            mesh.userData.facing as THREE.Vector3,
            0.04,
          )
        }
      }
      mesh.updateMatrix()
      this.batchCase(mesh, mesh.visible)
    }
    for (const batch of this.runBatches.values()) {
      batch.geometry = replacement
      batch.computeBoundingSphere()
    }
    previous.dispose()
  }

  // TODO: Validate
  setChannelButtons(enabled: boolean) {
    for (const button of this.channelButtons) {
      button.visible = enabled
      if (enabled) button.layers.enableAll()
      else button.layers.disableAll()
    }
  }

  // TODO: Validate
  setCounter(titles: StoreTitle[]) {
    if (this.counterStep === 0) return
    const loaded = new Map<string, THREE.Material>()
    for (const mesh of this.counterCases) {
      const material = mesh.userData.material as THREE.Material | undefined
      if (material) loaded.set((mesh.userData.title as StoreTitle).id, material)
      this.scene.remove(mesh)
    }
    this.counterCases = []
    for (const title of titles) {
      const shelved = this.mountedCases().find(
        (mesh) => (mesh.userData.title as StoreTitle).id === title.id,
      )
      const existingMaterial =
        (shelved?.userData.material as THREE.Material | undefined) ??
        loaded.get(title.id)
      const mesh = new THREE.Mesh(
        this.caseGeometry,
        existingMaterial ?? this.placeholderMaterial(title),
      )
      mesh.matrixAutoUpdate = false
      mesh.scale.setScalar(this.caseScale)
      mesh.rotation.order = "YXZ"
      mesh.userData = {
        title,
        basePosition: new THREE.Vector3(),
        facing: new THREE.Vector3(0, 0, 1),
        spin: randomOffset(),
        drift: randomOffset(),
        material: existingMaterial,
      }
      this.scene.add(mesh)
      this.counterCases.push(mesh)
    }
    for (const [index, held] of this.counterCases.entries()) {
      const row = Math.min(
        this.counterRows.length - 1,
        Math.floor(index / this.counterCapacity),
      )
      const anchor = this.counterRows[row]
      const within = index - row * this.counterCapacity
      this.settleCase(held, {
        position: anchor.clone().setX(anchor.x - this.counterStep * within),
        facing: new THREE.Vector3(0, 0, -1),
      })
    }
    this.applyLod()
  }

  // TODO: Validate
  private caseMaterial(texture: THREE.Texture) {
    return this.trackCase(
      this.unlit
        ? new THREE.MeshBasicMaterial({ map: texture })
        : new THREE.MeshStandardMaterial({
            map: texture,
            emissiveMap: texture,
            emissive: 0xffffff,
            emissiveIntensity: 0,
            roughness: 0.42,
            metalness: 0.06,
          }),
    )
  }

  // TODO: Validate
  setUnlit(enabled: boolean) {
    if (enabled === this.unlit) return
    this.unlit = enabled
    for (const mesh of this.mountedCases()) {
      const texture = mesh.userData.texture as THREE.Texture | undefined
      if (!texture) continue
      const previous = mesh.userData.material as
        | THREE.MeshStandardMaterial
        | THREE.MeshBasicMaterial
        | undefined
      if (previous) {
        this.caseMaterials.delete(previous)
        previous.dispose()
      }
      mesh.userData.material = this.caseMaterial(texture)
      if (mesh === this.focused) this.dressHighlight(mesh)
      else mesh.material = mesh.userData.material as THREE.Material
    }
  }

  // TODO: Validate
  setReflections(enabled: boolean) {
    this.reflections = enabled
    for (const material of this.caseMaterials) {
      if (!(material instanceof THREE.MeshStandardMaterial)) continue
      material.roughness = enabled ? (material.userData.roughness as number) : 1
      material.metalness = enabled ? (material.userData.metalness as number) : 0
      material.needsUpdate = true
    }
  }

  // TODO: Validate
  private placeholderMaterial(title: StoreTitle) {
    const bucket = Math.floor(genreHue(title.id) / 15)
    let material = this.placeholderMaterials.get(bucket)
    if (!material) {
      material = this.trackCase(
        new THREE.MeshStandardMaterial({
          color: new THREE.Color().setHSL((bucket * 15) / 360, 0.4, 0.26),
          roughness: 0.55,
          metalness: 0.04,
        }),
      )
      this.placeholderMaterials.set(bucket, material)
    }
    return material
  }

  // TODO: Validate
  private queueImage(mesh: THREE.Mesh) {
    const title = mesh.userData.title as StoreTitle
    if (!title.imageUrl || mesh.userData.imageQueued) return
    mesh.userData.imageQueued = true
    const generation = mesh.userData.generation as number
    // TODO: Validate
    const run = () => {
      this.activeImages++
      // TODO: Validate
      const finish = (loaded: HTMLImageElement | null) => {
        const current = mesh.userData.generation === generation
        if (!this.disposed && loaded && current) {
          const texture = createCaseTexture(title, loaded)
          mesh.userData.texture = texture
          mesh.userData.material = this.caseMaterial(texture)
          for (const held of this.counterCases) {
            if ((held.userData.title as StoreTitle).id === title.id) {
              held.material = mesh.userData.material as THREE.Material
            }
          }
          if (mesh === this.focused) this.dressHighlight(mesh)
          else mesh.material = mesh.userData.material as THREE.Material
        }
        this.activeImages--
        this.nextImage()
        this.reportCovers()
      }
      void loadStoreImage(title.imageUrl).then(finish)
    }
    this.pendingImages.push({ mesh, run })
    this.reportCovers()
  }

  // TODO: Validate
  private reportCovers() {
    const pending = this.pendingImages.length + this.activeImages
    if (this.disposed || pending === this.reportedCovers) return
    this.reportedCovers = pending
    this.callbacks.onCovers(pending)
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
    const nextX = position.x + this.velocity.x * delta
    if (!this.blocked(nextX, position.z)) position.x = nextX
    const nextZ = position.z + this.velocity.z * delta
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
    if (
      this.camera.position.distanceToSquared(this.lastFocusAt) < 0.0004 &&
      this.camera.quaternion.angleTo(this.lastFocusTurn) < 0.004
    ) {
      return
    }
    this.lastFocusAt.copy(this.camera.position)
    this.lastFocusTurn.copy(this.camera.quaternion)
    this.applyFocus(this.pick(0, 0, 3.2))
  }

  // TODO: Validate
  private pickTargets(far: number) {
    const reach = (far + 1.5) * (far + 1.5)
    const targets: THREE.Mesh[] = [...this.swatches, ...this.counterCases]
    // TODO: Validate
    const inReach = (mesh: THREE.Mesh) =>
      mesh.visible &&
      mesh
        .getWorldPosition(this.scratch)
        .distanceToSquared(this.camera.position) < reach
    for (const button of this.loaderButtons) {
      if (inReach(button)) targets.push(button)
    }
    for (const poster of this.posters) {
      if (inReach(poster)) targets.push(poster)
    }
    for (const index of this.nearRuns) {
      if (
        this.runCenters[index].distanceToSquared(this.camera.position) >
        (far + 6) * (far + 6)
      ) {
        continue
      }
      for (const mesh of this.runMeshes[index]) {
        if (mesh.position.distanceToSquared(this.camera.position) < reach) {
          targets.push(mesh)
        }
      }
    }
    return targets
  }

  // TODO: Validate
  private pick(x: number, y: number, far: number) {
    this.raycaster.setFromCamera(new THREE.Vector2(x, y), this.camera)
    this.raycaster.far = far
    const hit = this.raycaster.intersectObjects(
      [...this.pickTargets(far), ...this.shelves],
      false,
    )[0]
    if (!hit || this.shelves.includes(hit.object as THREE.InstancedMesh)) {
      return null
    }
    return hit.object as THREE.Mesh
  }

  // TODO: Validate
  private dressHighlight(mesh: THREE.Mesh) {
    const source = (mesh.userData.material ??
      this.placeholderMaterial(mesh.userData.title as StoreTitle)) as
      | THREE.MeshStandardMaterial
      | THREE.MeshBasicMaterial
      | undefined
    this.highlightMaterial.map = source?.map ?? null
    this.highlightMaterial.emissiveMap = source?.map ?? null
    this.highlightMaterial.emissiveIntensity =
      this.unlit && source?.map ? 1 : 0.3
    this.highlightMaterial.color.copy(
      source?.map
        ? new THREE.Color(0xffffff)
        : (source?.color ?? new THREE.Color()),
    )

    this.highlightMaterial.needsUpdate = true
    mesh.material = this.highlightMaterial
  }

  // TODO: Validate
  private applyFocus(mesh: THREE.Mesh | null) {
    if (mesh === this.focused) return
    if (this.focused?.userData.basePosition) {
      const previous = this.focused
      previous.material = (previous.userData.material ??
        this.placeholderMaterial(
          previous.userData.title as StoreTitle,
        )) as THREE.Material
      previous.position.copy(previous.userData.basePosition as THREE.Vector3)
      previous.updateMatrix()
      this.batchCase(previous, false)
    }
    this.focused = mesh
    if (!mesh) {
      this.callbacks.onFocus(null)
      return
    }
    if (!mesh.userData.basePosition) {
      this.callbacks.onFocus(null)
      return
    }
    this.dressHighlight(mesh)
    mesh.position
      .copy(mesh.userData.basePosition as THREE.Vector3)
      .addScaledVector(mesh.userData.facing as THREE.Vector3, 0.04)
    mesh.updateMatrix()
    this.batchCase(mesh, true)
    this.callbacks.onFocus(mesh.userData.title as StoreTitle)
  }

  // TODO: Validate
  private tick = () => {
    if (this.disposed) return
    this.animationHandle = requestAnimationFrame(this.tick)
    this.stats.update()
    const delta = Math.min(this.clock.getDelta(), 0.1)
    if (this.touch ? this.touchActive : this.controls.isLocked) {
      this.move(delta)
      this.moveLights()
      this.cullRuns()
      this.lodCountdown -= 1
      if (this.lodCountdown <= 0) {
        this.lodCountdown = 12
        this.updateLod()
      }
      if (!this.touch) this.updateFocus()
    }
    this.fallRain(delta)
    for (const leaf of this.doorLeaves) {
      const target = leaf.open ? leaf.swing : 0
      const turn = leaf.group.rotation.y
      if (Math.abs(target - turn) > 0.001) {
        leaf.group.rotation.y = turn + (target - turn) * 0.16
      }
    }
    this.renderer.info.reset()
    this.renderer.render(this.scene, this.camera)
    const now = performance.now()
    if (now - this.drawCallsShownAt > 500) {
      this.drawCallsShownAt = now
      const drawCalls = this.renderer.info.render.drawCalls
      this.drawCallPeak = Math.max(this.drawCallPeak, drawCalls)
      this.drawCallPanel.update(drawCalls, Math.max(this.drawCallPeak * 1.2, 1))
    }
  }

  // TODO: Validate
  setFog(range: number) {
    const reach = range >= 150 ? Number.POSITIVE_INFINITY : range
    if (reach === this.viewRange) return
    const had = this.scene.fog !== null
    this.viewRange = reach
    this.scene.fog =
      reach === Number.POSITIVE_INFINITY
        ? null
        : new THREE.Fog(0x07070b, reach * 0.45, reach)
    if (had !== (this.scene.fog !== null)) this.recompile()
    if (this.runs.length > 0) this.updateLod()
  }

  // TODO: Validate
  private recompile() {
    this.scene.traverse((object) => {
      const mesh = object as THREE.Mesh
      if (!mesh.isMesh) return
      const materials = Array.isArray(mesh.material)
        ? mesh.material
        : [mesh.material]
      for (const material of materials) material.needsUpdate = true
    })
  }

  // TODO: Validate
  setFloorColor(color: number) {
    if (!this.floorMaterial) return
    const hue = Math.round(
      new THREE.Color(color).getHSL({ h: 0, s: 0, l: 0 }, THREE.SRGBColorSpace)
        .h * 360,
    )
    this.floorMaterial.map?.dispose()
    this.floorMaterial.map = createCarpetTexture(hue)
    this.floorMaterial.map.repeat.copy(this.carpetRepeat)
    this.floorMaterial.needsUpdate = true
  }

  // TODO: Validate
  setRoomColor(color: number) {
    for (const material of this.roomMaterials) {
      material.color.set(color)
      material.needsUpdate = true
    }
  }

  // TODO: Validate
  setBoard(filters: string[], design: string[]) {
    if (!this.filterBoard) return
    const material = this.filterBoard.material as THREE.MeshBasicMaterial
    material.map?.dispose()
    material.map = createFilterBoardTexture(filters, design)
    material.needsUpdate = true
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
    const mesh = this.pick(
      ((clientX - rect.left) / rect.width) * 2 - 1,
      -((clientY - rect.top) / rect.height) * 2 + 1,
      4.5,
    )
    if (mesh && !mesh.userData.basePosition) {
      this.applyFocus(null)
      this.trigger(mesh)
      return
    }
    this.applyFocus(mesh)
    if (mesh) this.activateFocused()
  }

  // TODO: Validate
  activateFocused() {
    if (!this.focused) return
    if (!this.focused.userData.basePosition) {
      const target = this.focused
      this.applyFocus(null)
      this.trigger(target)
      return
    }
    const title = this.focused.userData.title as StoreTitle
    this.applyFocus(null)
    if (!this.touch) this.exit()
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
    this.cars?.dispose()
    this.litCars?.dispose()
    this.sidewalk?.dispose()
    this.trees?.dispose()
    this.forest?.dispose()
    this.terrain?.dispose()
    this.lamps?.dispose()
    for (const mesh of this.instanced) mesh.dispose()
    for (const mesh of this.casePool) {
      const material = mesh.userData.material as THREE.Material | undefined
      material?.dispose()
    }
    this.caseGeometry.dispose()
    this.tagGeometry.dispose()
    this.blockMaterial.dispose()
    this.stripGeometry.dispose()
    this.renderer.dispose()
    this.renderer.domElement.remove()
    this.statsPanel.remove()
  }
}
