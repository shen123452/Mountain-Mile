import * as THREE from 'three'
import { OrbitControls } from 'three/addons/controls/OrbitControls.js'
import type { TileData } from './terrain'
import type { IslandPalette } from './palettes'
import { createTree } from './decorations'

export interface IslandScene {
  setUnlocked(count: number): void
  setPalette(palette: IslandPalette): void
  setSelected(order: number | null): void
  dispose(): void
}

export function createIslandScene(canvas: HTMLCanvasElement, tiles: TileData[], palette: IslandPalette, onTileSelect?: (tile: TileData) => void): IslandScene {
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true, powerPreference: 'low-power' })
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.8))
  renderer.outputColorSpace = THREE.SRGBColorSpace
  const scene = new THREE.Scene()
  const camera = new THREE.PerspectiveCamera(38, 1, 0.1, 100)
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
  const cameraTarget = new THREE.Vector3(17, 19, 23)
  camera.position.copy(cameraTarget).multiplyScalar(reducedMotion ? 1 : 1.28)
  const controls = new OrbitControls(camera, canvas)
  controls.enableDamping = true
  controls.enablePan = false
  controls.minDistance = 18
  controls.maxDistance = 43
  controls.maxPolarAngle = Math.PI * 0.49
  controls.target.set(0, 0.5, 0)
  const ambient = new THREE.HemisphereLight('#ffffff', '#5c786b', 2.2)
  const sun = new THREE.DirectionalLight('#fff6db', 2.8)
  sun.position.set(-8, 16, 10)
  scene.add(ambient, sun)

  const box = new THREE.BoxGeometry(0.94, 1, 0.94)
  const decorations: THREE.Group[] = []
  const materials = new Map<string, THREE.MeshStandardMaterial>()
  function material(color: string): THREE.MeshStandardMaterial {
    let result = materials.get(color)
    if (!result) { result = new THREE.MeshStandardMaterial({ color, roughness: 0.92, flatShading: true }); materials.set(color, result) }
    return result
  }
  const selectionMaterial = new THREE.MeshBasicMaterial({ color: palette.accent, transparent: true, opacity: 0.78, side: THREE.DoubleSide, depthWrite: false })
  const groups = tiles.map(tile => {
    const group = new THREE.Group()
    group.position.set(tile.x, 0, tile.z)
    const top = tile.kind === 'river' || tile.kind === 'waterfall' || tile.kind === 'water' ? palette.water
      : tile.kind === 'rock' ? palette.rock : tile.kind === 'moss' ? palette.moss : palette.top
    const column = new THREE.Mesh(box, [material(palette.side), material(palette.side), material(top), material(palette.side), material(palette.side), material(palette.side)])
    column.scale.y = Math.max(0.2, tile.height + Math.max(0, tile.elevation) * 0.38)
    column.position.y = tile.elevation * 0.55 - column.scale.y * 0.5
    group.add(column)
    const selection = new THREE.Mesh(new THREE.RingGeometry(0.56, 0.7, 40), selectionMaterial)
    selection.rotation.x = -Math.PI / 2
    selection.position.y = column.position.y + column.scale.y * 0.5 + 0.035
    selection.visible = false
    group.add(selection)
    if (tile.kind === 'forest' && tile.unlockOrder % 3 === 0) {
      const tree = createTree(palette)
      tree.position.y = tile.elevation * 0.55
      group.add(tree)
      decorations.push(tree)
    }
    scene.add(group)
    group.visible = false
    group.userData.tile = tile
    return { group, tile, column, selection }
  })
  const shadow = new THREE.Mesh(new THREE.CircleGeometry(9, 48), new THREE.MeshBasicMaterial({ color: '#59796a', transparent: true, opacity: 0.1, depthWrite: false }))
  shadow.rotation.x = -Math.PI / 2
  shadow.position.y = -1.25
  shadow.scale.set(1.2, 0.85, 1)
  scene.add(shadow)

  let frame = 0
  let disposed = false
  const startedAt = performance.now()
  const appearing: Array<{ group: THREE.Group; start: number }> = []
  const raycaster = new THREE.Raycaster()
  const pointer = new THREE.Vector2()
  let pointerStart: { x: number; y: number } | null = null
  let selectedOrder: number | null = null
  const pointerDown = (event: PointerEvent) => { pointerStart = { x: event.clientX, y: event.clientY } }
  const pointerUp = (event: PointerEvent) => {
    if (!pointerStart || Math.hypot(event.clientX - pointerStart.x, event.clientY - pointerStart.y) > 6) { pointerStart = null; return }
    pointerStart = null
    const bounds = canvas.getBoundingClientRect()
    pointer.set((event.clientX - bounds.left) / bounds.width * 2 - 1, -((event.clientY - bounds.top) / bounds.height) * 2 + 1)
    raycaster.setFromCamera(pointer, camera)
    const hit = raycaster.intersectObjects(groups.map(item => item.group), true)[0]
    let group: THREE.Object3D | null = hit?.object ?? null
    while (group && group !== scene && !group.userData.tile) group = group.parent
    const tile = group?.userData.tile as TileData | undefined
    if (tile) { selectedOrder = tile.unlockOrder; groups.forEach(item => { item.selection.visible = item.tile.unlockOrder === selectedOrder }); onTileSelect?.(tile) }
  }
  canvas.addEventListener('pointerdown', pointerDown)
  canvas.addEventListener('pointerup', pointerUp)
  const resize = () => {
    const width = Math.max(1, canvas.clientWidth), height = Math.max(1, canvas.clientHeight)
    renderer.setSize(width, height, false)
    camera.aspect = width / height
    camera.updateProjectionMatrix()
  }
  const observer = new ResizeObserver(resize)
  observer.observe(canvas)
  resize()
  function render() {
    if (disposed) return
    const now = performance.now()
    if (!reducedMotion) {
      const flight = Math.min(1, (now - startedAt) / 900)
      camera.position.lerp(cameraTarget, 1 - Math.pow(1 - flight, 3))
      for (let i = appearing.length - 1; i >= 0; i--) {
        const item = appearing[i]
        const progress = Math.min(1, (now - item.start) / 650)
        item.group.scale.y = 0.08 + 0.92 * (1 - Math.pow(1 - progress, 3))
        if (progress === 1) appearing.splice(i, 1)
      }
    }
    controls.update()
    renderer.render(scene, camera)
    frame = requestAnimationFrame(render)
  }
  render()

  return {
    setUnlocked(count) { groups.forEach(({ group, tile }) => {
      const visible = tile.unlockOrder <= count
      if (visible && !group.visible) {
        group.scale.y = reducedMotion ? 1 : 0.08
        if (!reducedMotion) appearing.push({ group, start: performance.now() })
      }
      group.visible = visible
    }) },
    setPalette(next) {
      groups.forEach(({ tile, column, group }) => {
        const color = tile.kind === 'river' || tile.kind === 'waterfall' || tile.kind === 'water' ? next.water
          : tile.kind === 'rock' ? next.rock : tile.kind === 'moss' ? next.moss : next.top
        ;(column.material as THREE.Material[])[2] = material(color)
        ;(column.material as THREE.Material[])[0] = material(next.side)
        ;(column.material as THREE.Material[])[1] = material(next.side)
        ;(column.material as THREE.Material[])[3] = material(next.side)
        ;(column.material as THREE.Material[])[4] = material(next.side)
        ;(column.material as THREE.Material[])[5] = material(next.side)
      })
      decorations.forEach(tree => { const leaves = tree.children[1] as THREE.Mesh; (leaves.material as THREE.MeshStandardMaterial).color.set(next.tree) })
      ambient.groundColor.set(next.side)
      selectionMaterial.color.set(next.accent)
    },
    setSelected(order) {
      selectedOrder = order
      groups.forEach(item => { item.selection.visible = item.tile.unlockOrder === order })
    },
    dispose() {
      disposed = true
      cancelAnimationFrame(frame)
      observer.disconnect()
      canvas.removeEventListener('pointerdown', pointerDown)
      canvas.removeEventListener('pointerup', pointerUp)
      controls.dispose()
      box.dispose(); shadow.geometry.dispose(); selectionMaterial.dispose()
      groups.forEach(item => item.selection.geometry.dispose())
      decorations.forEach(tree => tree.children.forEach(child => {
        if (child instanceof THREE.Mesh) { child.geometry.dispose(); (child.material as THREE.Material).dispose() }
      }))
      ;(shadow.material as THREE.Material).dispose()
      materials.forEach(value => value.dispose())
      renderer.dispose()
    },
  }
}
