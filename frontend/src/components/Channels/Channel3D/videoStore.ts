// TODO: Validate
import * as THREE from "three"
import {
  CityGenerator,
  createBuildingMaterial,
} from "three/addons/generators/CityGenerator.js"
import {
  CarGenerator,
  type CarGeneratorPlacement,
} from "three/addons/generators/city/CarGenerator.js"
import { SidewalkGenerator } from "three/addons/generators/city/SidewalkGenerator.js"
import { PointerLockControls } from "three/examples/jsm/controls/PointerLockControls.js"
import { WebGPURenderer } from "three/webgpu"
import {
  createAisleSignTexture,
  createBeamTexture,
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
  createNightSkyTexture,
  createStoreSignTexture,
  createTagTexture,
  genreHue,
  type StoreTitle,
  shelfGenres,
} from "./caseTexture"
import { fetchTitleDetail } from "./titleDetail"

type Slot = { position: THREE.Vector3; facing: THREE.Vector3 }

type ShelfRun = {
  levels: Slot[][]
  order: Slot[]
  boards: THREE.Mesh[]
  aisle: number | null
  side: "left" | "right"
}

type AisleSign = {
  left: string[]
  right: string[]
  near: THREE.Mesh
  far: THREE.Mesh
}

// TODO: Validate
const randomOffset = () =>
  new THREE.Vector3(
    Math.random() - 0.5,
    Math.random() - 0.5,
    Math.random() - 0.5,
  )

// TODO: Validate
export const isTouchDevice = () =>
  window.matchMedia("(pointer: coarse)").matches

export type VideoStoreCallbacks = {
  onFocus: (title: StoreTitle | null) => void
  onActivate: (title: StoreTitle) => void
  onChannelAction: (action: "create" | "add") => void
  onFilters: () => void
  onLockChange: (locked: boolean) => void
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
  private cities: CityGenerator[] = []
  private cars: CarGenerator | null = null
  private sidewalk: SidewalkGenerator | null = null
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
  private animationHandle = 0
  private disposed = false
  private pendingImages: Array<{ mesh: THREE.Mesh; run: () => void }> = []
  private activeImages = 0
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
  private lights: Array<{ light: THREE.Light; base: number }> = []
  private laneAnchors: THREE.Vector3[] = []
  private laneGlows: THREE.Mesh[] = []
  private floorMaterial: THREE.MeshStandardMaterial | null = null
  private roomMaterials: THREE.MeshStandardMaterial[] = []
  private runMeshes: THREE.Mesh[][] = []
  private loaderButtons: THREE.Mesh[] = []
  private revealedRuns = new Set<number>()
  private realCases: THREE.Mesh[] = []
  private genreCases = new Map<string, THREE.Mesh[]>()
  private tagPool: THREE.Mesh[] = []
  private tagGeometry = new THREE.PlaneGeometry(0.155, 0.042)
  private stripMaterials = new Map<string, THREE.MeshStandardMaterial>()
  private placeholderMaterials = new Map<number, THREE.MeshStandardMaterial>()
  private runBlocks: THREE.Mesh[][] = []
  private runCenters: THREE.Vector3[] = []
  private blockFill: number[] = []
  private nearRuns = new Set<number>()
  private pickTargets: THREE.Mesh[] = []
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

    this.renderer = new WebGPURenderer({ antialias: true })
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
    this.renderer.setSize(container.clientWidth, container.clientHeight)
    this.renderer.sortObjects = false
    this.renderer.toneMapping = THREE.ACESFilmicToneMapping
    this.renderer.toneMappingExposure = 1
    container.appendChild(this.renderer.domElement)

    this.scene.background = new THREE.Color(0x07070b)
    this.scene.fog = new THREE.Fog(0x07070b, 12, 36)

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

    this.renderer.init().then(() => {
      if (this.disposed) return
      this.animationHandle = requestAnimationFrame(this.tick)
    })
  }

  // TODO: Validate
  private buildStore(slotCount: number, storeName: string) {
    const levels = [0.32, 0.68, 1.04, 1.4, 1.76]
    const slotWidth = 0.172
    const perLevel = 50
    const gondolaLength = perLevel * slotWidth
    const sides = Math.max(
      2,
      Math.ceil(slotCount / (levels.length * perLevel)) + 4,
    )
    const unitCount = Math.min(400, Math.max(1, Math.ceil(sides / 2)))
    const width = unitCount * 2 + 2.9
    const depth = gondolaLength + 6
    this.camera.position.set(width / 2 - 1.8, 1.65, depth / 2 - 1.05)
    this.camera.lookAt(-width / 2 + 1.2, 1.3, -depth / 2 + 1.2)

    this.floorMaterial = new THREE.MeshStandardMaterial({
      map: createCarpetTexture(),
      roughness: 0.95,
    })
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
    const ceiling = new THREE.Mesh(
      new THREE.PlaneGeometry(width, depth),
      new THREE.MeshStandardMaterial({ map: ceilingTexture, roughness: 0.92 }),
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

    for (const light of [
      new THREE.AmbientLight(0xc6cfff, 0.38),
      new THREE.HemisphereLight(0xe6ecff, 0x1a1626, 0.55),
    ]) {
      this.lights.push({ light, base: light.intensity })
      this.scene.add(light)
    }

    const bays = Math.max(4, Math.round(width / 1.3))
    const bayWidth = width / bays
    const doorBay = Math.min(
      bays - 2,
      Math.max(0, Math.round((width - 6.6) / bayWidth) - 1),
    )
    const doorCenter = -width / 2 + bayWidth * (doorBay + 1)
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

    const lotUnits = Math.ceil(width / 19.9) + 2
    const lotWidth = lotUnits * 19.9
    const sky = new THREE.Mesh(
      new THREE.PlaneGeometry(lotWidth + 320, 150),
      new THREE.MeshBasicMaterial({
        map: createNightSkyTexture(),
        fog: false,
      }),
    )
    sky.position.set(0, 50, depth / 2 + 190)
    sky.rotation.y = Math.PI
    this.scene.add(sky)

    const apron = new THREE.Mesh(
      new THREE.PlaneGeometry(lotWidth + 60, 84),
      new THREE.MeshBasicMaterial({ color: 0x101016, fog: false }),
    )
    apron.position.set(0, -0.12, depth / 2 + 42)
    apron.rotation.x = -Math.PI / 2
    this.scene.add(apron)

    const cityLamps: THREE.Vector3[] = []
    for (const [cityX, cityZ, turn, blocksX] of [
      [0, depth / 2 + 78, 0, Math.max(2, Math.ceil(lotWidth / 64))],
      [-lotWidth / 2 - 44, depth / 2 + 26, Math.PI / 2, 2],
      [lotWidth / 2 + 44, depth / 2 + 26, -Math.PI / 2, 2],
    ] as const) {
      const city = new CityGenerator({
        seed: Math.floor(Math.random() * 1000),
        street: 16,
        lot: 24,
        lotsX: 2,
        lotsZ: 2,
        blocksX,
        blocksZ: 1,
      })
      const block = city.build({
        building: createBuildingMaterial(city.layout, city.seedNode),
      })
      block.traverse((object) => {
        const mesh = object as THREE.Mesh
        if (!mesh.isMesh) return
        const materials = Array.isArray(mesh.material)
          ? mesh.material
          : [mesh.material]
        for (const material of materials) {
          ;(material as THREE.Material & { fog: boolean }).fog = false
        }
      })
      block.position.set(cityX, -0.12, cityZ)
      block.rotation.y = turn
      this.scene.add(block)
      this.cities.push(city)

      block.updateMatrixWorld(true)
      const lamps = city.furniture.streetlight.mesh
      if (lamps) {
        const placement = new THREE.Matrix4()
        const head = new THREE.Vector3(
          0,
          city.furniture.streetlight.parameters.height,
          city.furniture.streetlight.parameters.reach,
        )
        for (let index = 0; index < lamps.count; index++) {
          lamps.getMatrixAt(index, placement)
          cityLamps.push(
            head
              .clone()
              .applyMatrix4(placement)
              .applyMatrix4(lamps.matrixWorld),
          )
        }
      }
    }

    const moon = new THREE.DirectionalLight(0xc3d4ff, 0.7)
    moon.position.set(-90, 120, depth / 2 + 170)
    moon.target.position.set(0, 0, depth / 2 + 60)
    this.scene.add(moon)
    this.scene.add(moon.target)

    this.sidewalk = new SidewalkGenerator({
      width: Math.max(width, lotWidth),
      depth: 2.3,
      height: 0.15,
      radius: 0.6,
    })
    const walk = this.sidewalk.build([
      new THREE.Matrix4().makeTranslation(0, -0.12, depth / 2 + 1.15),
    ])
    walk.traverse((object) => {
      const mesh = object as THREE.Mesh
      if (!mesh.isMesh) return
      const materials = Array.isArray(mesh.material)
        ? mesh.material
        : [mesh.material]
      for (const material of materials) {
        ;(material as THREE.Material & { fog: boolean }).fog = false
      }
    })
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

    const parked: CarGeneratorPlacement[] = []
    for (let spot = 0; spot < Math.floor(lotWidth / 2.6); spot++) {
      if (Math.random() < 0.5) continue
      const matrix = new THREE.Matrix4().makeRotationY(
        (Math.random() < 0.7 ? Math.PI : 0) + (Math.random() - 0.5) * 0.08,
      )
      matrix.setPosition(
        -lotWidth / 2 + 2.6 * (spot + 0.5) + (Math.random() - 0.5) * 0.3,
        -0.1,
        depth / 2 + 4.9 + (Math.random() - 0.5) * 0.5,
      )
      parked.push({
        matrix,
        color:
          Math.random() < 0.15
            ? CarGenerator.taxiColor
            : [0x9aa3ad, 0x2f3a4a, 0x7d2b2b, 0xd7d9dc, 0x1d2126, 0x35543f][
                Math.floor(Math.random() * 6)
              ],
      })
    }
    if (parked.length > 0) {
      this.cars = new CarGenerator()
      const fleet = this.cars.build(parked)
      fleet.traverse((object) => {
        const mesh = object as THREE.Mesh
        if (!mesh.isMesh) return
        const materials = Array.isArray(mesh.material)
          ? mesh.material
          : [mesh.material]
        for (const material of materials) {
          ;(material as THREE.Material & { fog: boolean }).fog = false
        }
      })
      this.scene.add(fleet)
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
      }
    }

    const poleMaterial = new THREE.MeshBasicMaterial({
      color: 0x2a2c34,
      fog: false,
    })
    const lampMaterial = new THREE.MeshBasicMaterial({
      color: 0xffeec2,
      fog: false,
    })
    const beamMaterial = new THREE.MeshBasicMaterial({
      map: createBeamTexture(),
      transparent: true,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
      side: THREE.DoubleSide,
      fog: false,
    })
    const poolMaterial = new THREE.MeshBasicMaterial({
      map: createGlowTexture(),
      transparent: true,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
      fog: false,
    })
    const beamGeometry = new THREE.ConeGeometry(2.4, 5.2, 18, 1, true)
    const poolGeometry = new THREE.CircleGeometry(2.6, 24)

    if (cityLamps.length > 0) {
      const drop = cityLamps[0].y + 0.12
      const cityBeamGeometry = new THREE.ConeGeometry(
        drop * 0.42,
        drop,
        18,
        1,
        true,
      )
      const cityPoolGeometry = new THREE.CircleGeometry(drop * 0.48, 24)
      for (const lamp of cityLamps) {
        const beam = new THREE.Mesh(cityBeamGeometry, beamMaterial)
        beam.position.set(lamp.x, -0.12 + drop / 2, lamp.z)
        beam.matrixAutoUpdate = false
        beam.updateMatrix()
        this.scene.add(beam)

        const pool = new THREE.Mesh(cityPoolGeometry, poolMaterial)
        pool.position.set(lamp.x, -0.08, lamp.z)
        pool.rotation.x = -Math.PI / 2
        pool.matrixAutoUpdate = false
        pool.updateMatrix()
        this.scene.add(pool)
      }
    }
    const trunkGeometry = new THREE.CylinderGeometry(0.11, 0.17, 1.7, 6)
    const canopyGeometry = new THREE.IcosahedronGeometry(0.95, 1)
    const trunkMaterial = new THREE.MeshBasicMaterial({
      color: 0x2b2118,
      fog: false,
    })
    const canopyMaterial = new THREE.MeshBasicMaterial({
      color: 0x1f3526,
      fog: false,
    })
    for (const islandX of islandXs) {
      for (const treeZ of [17.5, 24.5, 31, 37.5, 44.5]) {
        const trunk = new THREE.Mesh(trunkGeometry, trunkMaterial)
        trunk.position.set(islandX, 0.79, depth / 2 + treeZ)
        this.scene.add(trunk)
        for (const [leafX, leafY, leafZ, size] of [
          [0, 2.15, 0, 1],
          [0.55, 1.68, 0.3, 0.68],
          [-0.5, 1.75, -0.35, 0.6],
        ] as const) {
          const canopy = new THREE.Mesh(canopyGeometry, canopyMaterial)
          canopy.position.set(islandX + leafX, leafY, depth / 2 + treeZ + leafZ)
          canopy.scale.setScalar(size)
          this.scene.add(canopy)
        }
      }
    }
    for (const poleX of islandXs) {
      for (const poleZ of [20.5, 31, 41.5]) {
        const mast = new THREE.Mesh(
          new THREE.BoxGeometry(0.16, 5.4, 0.16),
          poleMaterial,
        )
        mast.position.set(poleX, 2.58, depth / 2 + poleZ)
        this.scene.add(mast)
        const crossbar = new THREE.Mesh(
          new THREE.BoxGeometry(3, 0.13, 0.13),
          poleMaterial,
        )
        crossbar.position.set(poleX, 5.21, depth / 2 + poleZ)
        this.scene.add(crossbar)

        for (const side of [-1, 1]) {
          const lampX = poleX + side * 1.42
          const lamp = new THREE.Mesh(
            new THREE.BoxGeometry(0.46, 0.11, 0.26),
            lampMaterial,
          )
          lamp.position.set(lampX, 5.1, depth / 2 + poleZ)
          this.scene.add(lamp)

          const beam = new THREE.Mesh(beamGeometry, beamMaterial)
          beam.position.set(lampX, 2.44, depth / 2 + poleZ)
          this.scene.add(beam)

          const pool = new THREE.Mesh(poolGeometry, poolMaterial)
          pool.position.set(lampX, -0.08, depth / 2 + poleZ)
          pool.rotation.x = -Math.PI / 2
          this.scene.add(pool)
        }
      }
    }

    const housingMaterial = new THREE.MeshStandardMaterial({
      color: 0x3c3f47,
      roughness: 0.55,
      metalness: 0.35,
    })
    const diffuserMaterial = new THREE.MeshBasicMaterial({
      map: createDiffuserTexture(),
      toneMapped: false,
    })
    const glowMaterial = new THREE.MeshBasicMaterial({
      map: createGlowTexture(),
      transparent: true,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
    })
    const housingGeometry = new THREE.BoxGeometry(
      tileX * 0.98,
      0.07,
      tileZ * 0.98,
    )
    const diffuserGeometry = new THREE.PlaneGeometry(tileX * 0.88, tileZ * 0.92)
    for (let column = 1; column < columns; column += 3) {
      const x = -width / 2 + (column + 0.5) * tileX
      for (let row = 1; row < rows; row += 2) {
        const z = -depth / 2 + (row + 0.5) * tileZ
        const housing = new THREE.Mesh(housingGeometry, housingMaterial)
        housing.position.set(x, 3.168, z)
        housing.matrixAutoUpdate = false
        housing.updateMatrix()
        this.scene.add(housing)

        const diffuser = new THREE.Mesh(diffuserGeometry, diffuserMaterial)
        diffuser.position.set(x, 3.131, z)
        diffuser.rotation.x = Math.PI / 2
        diffuser.matrixAutoUpdate = false
        diffuser.updateMatrix()
        this.scene.add(diffuser)

        const glow = new THREE.Mesh(
          new THREE.PlaneGeometry(3.6, 3.6),
          glowMaterial,
        )
        glow.position.set(x, 0.02, z)
        glow.rotation.x = -Math.PI / 2
        glow.matrixAutoUpdate = false
        glow.updateMatrix()
        glow.visible = false
        this.scene.add(glow)
        this.laneGlows.push(glow)
        this.laneAnchors.push(new THREE.Vector3(x, 2.95, z))
      }
    }
    const lamps = 6
    for (let index = 0; index < lamps; index++) {
      const lamp = new THREE.PointLight(0xfff1d8, 3.6, 26, 1)
      lamp.position.set(((index + 0.5) / lamps - 0.5) * width, 2.98, -0.5)
      this.lights.push({ light: lamp, base: lamp.intensity })
      this.scene.add(lamp)
    }
    const entranceLamp = new THREE.PointLight(0x9ad7ff, 2.6, 24, 1)
    this.lights.push({ light: entranceLamp, base: entranceLamp.intensity })
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
      const x = (unit - (unitCount - 1) / 2) * 2
      const zStart = -0.5 - gondolaLength / 2

      const spine = new THREE.Mesh(
        new THREE.BoxGeometry(0.08, 2.05, gondolaLength),
        frameMaterial,
      )
      spine.position.set(x, 1.025, -0.5)
      this.scene.add(spine)

      const base = new THREE.Mesh(
        new THREE.BoxGeometry(0.35, 0.28, gondolaLength),
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
            new THREE.BoxGeometry(0.135, 0.03, gondolaLength),
            shelfMaterial,
          )
          board.position.set(x + side * 0.0675, level - 0.015, -0.5)
          this.scene.add(board)
          boards.push(board)

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
          boards,
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

    const counterMaterial = new THREE.MeshStandardMaterial({
      color: 0xd8b13a,
      roughness: 0.6,
    })
    this.roomMaterials.push(wallMaterial, counterMaterial)
    const counter = new THREE.Mesh(
      new THREE.BoxGeometry(2.6, 1.05, 0.7),
      counterMaterial,
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

    for (const level of [0.9, 1.22, 1.54]) {
      const holdBoard = new THREE.Mesh(
        new THREE.BoxGeometry(2.6, 0.03, 0.135),
        shelfMaterial,
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

    for (let aisle = 0; aisle <= unitCount; aisle++) {
      const signX = (aisle - unitCount / 2) * 2
      const near = new THREE.Mesh(
        new THREE.PlaneGeometry(1.8, 0.45),
        new THREE.MeshBasicMaterial({
          map: createAisleSignTexture([], []),
        }),
      )
      near.position.set(signX, 2.46, -0.5 + gondolaLength / 2 + 0.22)
      const far = new THREE.Mesh(
        new THREE.PlaneGeometry(1.8, 0.45),
        new THREE.MeshBasicMaterial({
          map: createAisleSignTexture([], []),
        }),
      )
      far.position.set(signX, 2.46, -0.5 - gondolaLength / 2 - 0.22)
      far.rotation.y = Math.PI
      const nearBack = new THREE.Mesh(near.geometry, far.material)
      nearBack.position.copy(near.position)
      nearBack.rotation.y = Math.PI
      const farBack = new THREE.Mesh(far.geometry, near.material)
      farBack.position.copy(far.position)
      this.scene.add(near)
      this.scene.add(far)
      this.scene.add(nearBack)
      this.scene.add(farBack)
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
    this.runBlocks = runs.map(() => [])
    this.blockFill = runs.map(() => -1)
    this.runCenters = runs.map((run) => {
      const row = run.levels[Math.floor(run.levels.length / 2)]
      return row[0].position.clone().lerp(row[row.length - 1].position, 0.5)
    })
    for (let index = 0; index < runs.length; index++) {
      const slot = runs[index].order[0]
      const button = new THREE.Mesh(
        new THREE.PlaneGeometry(0.62, 0.194),
        new THREE.MeshBasicMaterial({ map: createLoaderTexture() }),
      )
      button.position
        .copy(slot.position)
        .addScaledVector(slot.facing, 0.42)
        .setY(1.58)
      button.rotation.y = Math.atan2(slot.facing.x, slot.facing.z)
      button.userData = { run: index }
      button.matrixAutoUpdate = false
      button.updateMatrix()
      this.scene.add(button)
      this.loaderButtons.push(button)
    }
    this.pickTargets = [...this.loaderButtons, ...this.swatches]
  }

  // TODO: Validate
  private refreshBlocks() {
    for (let index = 0; index < this.runs.length; index++) {
      const filled = this.runMeshes[index].length
      if (filled === this.blockFill[index]) continue
      this.blockFill[index] = filled

      for (const block of this.runBlocks[index]) {
        block.geometry.dispose()
        this.scene.remove(block)
      }
      this.runBlocks[index] = []
      if (filled === 0) continue

      const run = this.runs[index]
      const columns = Math.min(
        run.levels[0].length,
        Math.ceil(filled / run.levels.length),
      )
      const along = run.levels[0][0].facing.x !== 0 ? "z" : "x"
      for (const row of run.levels) {
        const near = row[row.length - 1].position
        const far = row[row.length - columns].position
        const span = Math.abs(near[along] - far[along]) + 0.172
        const block = new THREE.Mesh(
          along === "z"
            ? new THREE.BoxGeometry(0.02, 0.19, span)
            : new THREE.BoxGeometry(span, 0.19, 0.02),
          this.blockMaterial,
        )
        block.position.copy(near).lerp(far, 0.5)
        block.matrixAutoUpdate = false
        block.updateMatrix()
        block.visible = !this.nearRuns.has(index)
        this.scene.add(block)
        this.runBlocks[index].push(block)
      }
    }
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
        continue
      }
      if (near) {
        this.nearRuns.delete(index)
        changed = true
      }
    }
    if (changed) this.applyLod()
  }

  // TODO: Validate
  private moveLights() {
    for (const [index, glow] of this.laneGlows.entries()) {
      glow.visible =
        this.laneAnchors[index].distanceToSquared(this.camera.position) < 900
    }
  }

  // TODO: Validate
  private applyLod() {
    this.pickTargets = [
      ...this.loaderButtons,
      ...this.posters,
      ...this.swatches,
      ...this.counterCases,
    ]
    for (let index = 0; index < this.runs.length; index++) {
      const near = this.nearRuns.has(index)
      for (const block of this.runBlocks[index]) block.visible = !near
      for (const mesh of this.runMeshes[index]) mesh.visible = near
      if (near) this.pickTargets.push(...this.runMeshes[index])
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
      const genreNames = shelfGenres(title)
      for (const genre of genreNames.length ? genreNames : ["Unknown"]) {
        const shelved = this.genreCases.get(genre) ?? []
        shelved.push(this.buildCase(title))
        this.genreCases.set(genre, shelved)
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
    const named = [...this.genreCases.keys()]
      .filter((genre) => genre !== "Unknown")
      .sort((left, right) => right.localeCompare(left))
    return this.genreCases.has("Unknown") ? [...named, "Unknown"] : named
  }

  // TODO: Validate
  private layoutStore() {
    this.runMeshes = this.runs.map(() => [])
    for (const mesh of this.realCases) mesh.visible = false
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
        this.runMeshes[runIndex].push(mesh)
        if (this.revealedRuns.has(runIndex)) this.queueImage(mesh)
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
      .addScaledVector(near.facing, 0.056)
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
      .addScaledVector(slot.facing, 0.056)
      .setY(slot.position.y - 0.117)
    mesh.rotation.y = Math.atan2(slot.facing.x, slot.facing.z)
  }

  // TODO: Validate
  private dressPosters() {
    const seen = new Set<string>()
    const candidates: StoreTitle[] = []
    for (const mesh of this.realCases) {
      const title = mesh.userData.title as StoreTitle
      if (!title.imageUrl || seen.has(title.id)) continue
      seen.add(title.id)
      candidates.push(title)
    }
    if (candidates.length === 0) return

    candidates.sort(
      (left, right) => (right.popularity ?? -1) - (left.popularity ?? -1),
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
        basePosition: poster.position.clone(),
        facing: new THREE.Vector3(
          Math.sin(poster.rotation.y),
          0,
          Math.cos(poster.rotation.y),
        ),
        material: poster.material,
      }
      this.paintPoster(poster, title)
    }
  }

  // TODO: Validate
  private async paintPoster(poster: THREE.Mesh, title: StoreTitle) {
    const detail = await fetchTitleDetail(title.id)
    if (this.disposed) return
    const source = detail.poster_url ?? title.imageUrl
    if (!source) return
    const image = new Image()
    image.crossOrigin = "anonymous"
    image.referrerPolicy = "no-referrer"
    // TODO: Validate
    const finish = (loaded: HTMLImageElement | null) => {
      if (this.disposed || !loaded) return
      const canvas = createCaseCanvas(title, loaded, 3)
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
    image.onload = () => finish(image)
    image.onerror = () => finish(null)
    image.src = source
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
    this.reveal(mesh.userData.run as number)
  }

  // TODO: Validate
  private reveal(runIndex: number) {
    this.revealedRuns.add(runIndex)
    const button = this.loaderButtons[runIndex]
    button.visible = false
    button.layers.disableAll()
    for (const mesh of this.runMeshes[runIndex]) this.queueImage(mesh)
    for (let concurrent = 0; concurrent < 6; concurrent++) this.nextImage()
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
  setAskew(value: number) {
    this.askew = value / 50
    for (const mesh of [...this.realCases, ...this.counterCases]) {
      const slot = mesh.userData.slot as THREE.Vector3 | undefined
      if (!slot) continue
      this.settleCase(mesh, {
        position: slot,
        facing: mesh.userData.facing as THREE.Vector3,
      })
    }
  }

  // TODO: Validate
  setLights(level: number) {
    const strength = level
    for (const { light, base } of this.lights) {
      light.intensity = base * strength
    }
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
    for (const mesh of this.realCases) {
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
      const shelved = this.realCases.find(
        (mesh) => (mesh.userData.title as StoreTitle).id === title.id,
      )
      const carried =
        (shelved?.userData.material as THREE.Material | undefined) ??
        loaded.get(title.id)
      const mesh = new THREE.Mesh(
        this.caseGeometry,
        carried ?? this.placeholderMaterial(title),
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
        material: carried,
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
    for (const mesh of this.realCases) {
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
  private buildCase(title: StoreTitle) {
    const mesh = new THREE.Mesh(
      this.caseGeometry,
      this.placeholderMaterial(title),
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
    }
    this.scene.add(mesh)
    this.caseMeshes.push(mesh)
    this.realCases.push(mesh)
    return mesh
  }

  // TODO: Validate
  private queueImage(mesh: THREE.Mesh) {
    const title = mesh.userData.title as StoreTitle
    if (!title.imageUrl || mesh.userData.imageQueued) return
    mesh.userData.imageQueued = true
    // TODO: Validate
    const run = () => {
      this.activeImages++
      const image = new Image()
      image.crossOrigin = "anonymous"
      image.referrerPolicy = "no-referrer"
      // TODO: Validate
      const finish = (loaded: HTMLImageElement | null) => {
        if (!this.disposed && loaded) {
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
    this.applyFocus(this.pick(0, 0, 3.2))
  }

  // TODO: Validate
  private pick(x: number, y: number, far: number) {
    this.raycaster.setFromCamera(new THREE.Vector2(x, y), this.camera)
    this.raycaster.far = far
    const hit = this.raycaster.intersectObjects(this.pickTargets, false)[0]
    return (hit?.object as THREE.Mesh | undefined) ?? null
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
    this.callbacks.onFocus(mesh.userData.title as StoreTitle)
  }

  // TODO: Validate
  private tick = () => {
    if (this.disposed) return
    this.animationHandle = requestAnimationFrame(this.tick)
    const delta = Math.min(this.clock.getDelta(), 0.1)
    if (this.touch ? this.touchActive : this.controls.isLocked) {
      this.move(delta)
      this.lodCountdown -= 1
      if (this.lodCountdown <= 0) {
        this.lodCountdown = 12
        this.updateLod()
        this.moveLights()
      }
      if (!this.touch) this.updateFocus()
    }
    for (const leaf of this.doorLeaves) {
      const target = leaf.open ? leaf.swing : 0
      const turn = leaf.group.rotation.y
      if (Math.abs(target - turn) > 0.001) {
        leaf.group.rotation.y = turn + (target - turn) * 0.16
      }
    }
    this.renderer.render(this.scene, this.camera)
  }

  // TODO: Validate
  setFloorColor(color: number) {
    if (!this.floorMaterial) return
    const hue = Math.round(
      new THREE.Color(color).getHSL({ h: 0, s: 0, l: 0 }).h * 360,
    )
    this.floorMaterial.map?.dispose()
    this.floorMaterial.map = createCarpetTexture(hue)
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
    for (const city of this.cities) city.dispose()
    this.cars?.dispose()
    this.sidewalk?.dispose()
    this.caseGeometry.dispose()
    this.tagGeometry.dispose()
    this.blockMaterial.dispose()
    this.stripGeometry.dispose()
    this.renderer.dispose()
    this.renderer.domElement.remove()
  }
}
