// TODO: Validate
import * as THREE from "three"
import { PointerLockControls } from "three/examples/jsm/controls/PointerLockControls.js"
import {
  createCarpetTexture,
  createCaseTexture,
  createSignTexture,
  type StoreTitle,
} from "./caseTexture"

type Slot = { position: THREE.Vector3; facing: THREE.Vector3 }

export type VideoStoreCallbacks = {
  onFocus: (title: StoreTitle | null) => void
  onActivate: (title: StoreTitle) => void
  onLockChange: (locked: boolean) => void
}

// TODO: Validate
const buildCaseGeometry = () => {
  const geometry = new THREE.BoxGeometry(0.135, 0.19, 0.015)
  const spine = { x: 168 / 256, y: 0.125, w: 24 / 256, h: 224 / 256 }
  const edge = { x: 192 / 256, y: 0.125, w: 64 / 256, h: 224 / 256 }
  const front = { x: 0, y: 0.125, w: 168 / 256, h: 224 / 256 }
  const rects = [spine, spine, edge, edge, front, edge]
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
  private pendingImages: Array<{ position: THREE.Vector3; run: () => void }> =
    []
  private activeImages = 0
  private slots: Slot[] = []
  private caseGeometry = buildCaseGeometry()
  private resizeObserver: ResizeObserver

  // TODO: Validate
  constructor(
    container: HTMLElement,
    capacity: number,
    channelName: string,
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

    this.buildStore(capacity, channelName)

    this.controls.addEventListener("lock", this.handleLock)
    this.controls.addEventListener("unlock", this.handleUnlock)
    window.addEventListener("keydown", this.handleKeyDown)
    window.addEventListener("keyup", this.handleKeyUp)
    this.resizeObserver = new ResizeObserver(this.handleResize)
    this.resizeObserver.observe(container)

    this.animationHandle = requestAnimationFrame(this.tick)
  }

  // TODO: Validate
  private buildStore(capacity: number, channelName: string) {
    const levels = [0.32, 0.68, 1.04, 1.4, 1.76]
    const slotWidth = 0.172
    const unitCount = Math.min(6, Math.max(1, Math.ceil(capacity / 420)))
    const slotsPerMeter = (levels.length * 2) / slotWidth
    const gondolaLength = Math.min(
      16,
      Math.max(4, (capacity * 1.35) / (unitCount * slotsPerMeter)),
    )
    const width = unitCount * 3.3 + 3.4
    const depth = gondolaLength + 6
    this.limit.set(width / 2 - 0.45, depth / 2 - 0.45)
    this.camera.position.set(0, 1.65, depth / 2 - 1.4)

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
        map: createSignTexture(channelName.toUpperCase()),
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
      if (lane < 6) {
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
    const slots: Slot[] = []

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

      for (const level of levels) {
        const board = new THREE.Mesh(
          new THREE.BoxGeometry(0.58, 0.03, gondolaLength),
          shelfMaterial,
        )
        board.position.set(x, level - 0.015, -0.5)
        this.scene.add(board)
      }

      const perLevel = Math.floor(gondolaLength / slotWidth)
      const margin = (gondolaLength - perLevel * slotWidth) / 2
      for (const level of levels) {
        for (const side of [1, -1]) {
          for (let index = 0; index < perLevel; index++) {
            slots.push({
              position: new THREE.Vector3(
                x + side * 0.215,
                level + 0.096,
                zStart + margin + slotWidth * (index + 0.5),
              ),
              facing: new THREE.Vector3(side, 0, 0),
            })
          }
        }
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
    for (const level of levels) {
      for (let index = 0; index < wallPerLevel; index++) {
        slots.push({
          position: new THREE.Vector3(
            -wallShelfLength / 2 + wallMargin + slotWidth * (index + 0.5),
            level + 0.096,
            -depth / 2 + 0.31,
          ),
          facing: new THREE.Vector3(0, 0, 1),
        })
      }
    }
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

    this.slots = slots
  }

  // TODO: Validate
  addTitles(titles: StoreTitle[]) {
    const placed = Math.min(titles.length, this.slots.length)
    for (let index = this.caseMeshes.length; index < placed; index++) {
      const title = titles[index]
      const slot = this.slots[index]
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
      mesh.position.copy(slot.position)
      mesh.rotation.y = Math.atan2(slot.facing.x, slot.facing.z)
      mesh.rotation.z = (Math.random() - 0.5) * 0.05
      mesh.userData = {
        title,
        basePosition: slot.position.clone(),
        facing: slot.facing.clone(),
      }
      this.scene.add(mesh)
      this.caseMeshes.push(mesh)
      if (title.imageUrl) this.queueImage(title, material, slot.position)
    }

    for (let concurrent = 0; concurrent < 6; concurrent++) this.nextImage()
  }

  // TODO: Validate
  private queueImage(
    title: StoreTitle,
    material: THREE.MeshStandardMaterial,
    position: THREE.Vector3,
  ) {
    // TODO: Validate
    const run = () => {
      this.activeImages++
      const image = new Image()
      image.crossOrigin = "anonymous"
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
    this.pendingImages.push({ position: position.clone(), run })
  }

  // TODO: Validate
  private nextImage() {
    if (this.disposed || this.activeImages >= 6) return
    if (this.pendingImages.length === 0) return
    let nearest = 0
    let shortest = Number.POSITIVE_INFINITY
    for (let index = 0; index < this.pendingImages.length; index++) {
      const distance = this.pendingImages[index].position.distanceToSquared(
        this.camera.position,
      )
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

    const crouching = this.pressed.has("KeyC")
    const running =
      !crouching &&
      (this.pressed.has("ShiftLeft") || this.pressed.has("ShiftRight"))
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
    this.raycaster.setFromCamera(new THREE.Vector2(0, 0), this.camera)
    this.raycaster.far = 3.2
    const hit = this.raycaster.intersectObjects(this.caseMeshes, false)[0]
    const mesh = (hit?.object as THREE.Mesh | undefined) ?? null
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
    if (this.controls.isLocked) {
      this.move(delta)
      this.updateFocus()
    }
    this.renderer.render(this.scene, this.camera)
  }

  // TODO: Validate
  lock() {
    this.controls.lock()
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
    this.renderer.dispose()
    this.renderer.domElement.remove()
  }
}
