import * as THREE from 'three'
import { OrbitControls } from 'three/addons/controls/OrbitControls.js'
import type { TileData } from './terrain'
import type { IslandPalette } from './palettes'
import { createTree } from './decorations'

export interface IslandScene {
  setUnlocked(count: number): void
  setPalette(palette: IslandPalette): void
  dispose(): void
}

export function createIslandScene(canvas: HTMLCanvasElement, tiles: TileData[], palette: IslandPalette): IslandScene {
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true, powerPreference: 'low-power' })
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.8))
  renderer.outputColorSpace = THREE.SRGBColorSpace
  const scene = new THREE.Scene()
  const camera = new THREE.PerspectiveCamera(38, 1, 0.1, 100)
  camera.position.set(17, 19, 23)
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
  const groups = tiles.map(tile => {
    const group = new THREE.Group()
    group.position.set(tile.x, 0, tile.z)
    const top = tile.kind === 'river' || tile.kind === 'waterfall' || tile.kind === 'water' ? palette.water
      : tile.kind === 'rock' ? palette.rock : tile.kind === 'moss' ? palette.moss : palette.top
    const column = new THREE.Mesh(box, [material(palette.side), material(palette.side), material(top), material(palette.side), material(palette.side), material(palette.side)])
    column.scale.y = Math.max(0.2, tile.height + Math.max(0, tile.elevation) * 0.38)
    column.position.y = tile.elevation * 0.55 - column.scale.y * 0.5
    group.add(column)
    if (tile.kind === 'forest' && tile.unlockOrder % 3 === 0) {
      const tree = createTree(palette)
      tree.position.y = tile.elevation * 0.55
      group.add(tree)
      decorations.push(tree)
    }
    scene.add(group)
    return { group, tile, column }
  })
  const shadow = new THREE.Mesh(new THREE.CircleGeometry(9, 48), new THREE.MeshBasicMaterial({ color: '#59796a', transparent: true, opacity: 0.1, depthWrite: false }))
  shadow.rotation.x = -Math.PI / 2
  shadow.position.y = -1.25
  shadow.scale.set(1.2, 0.85, 1)
  scene.add(shadow)

  let frame = 0
  let disposed = false
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
    controls.update()
    renderer.render(scene, camera)
    frame = requestAnimationFrame(render)
  }
  render()

  return {
    setUnlocked(count) { groups.forEach(({ group, tile }) => { group.visible = tile.unlockOrder <= count }) },
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
    },
    dispose() {
      disposed = true
      cancelAnimationFrame(frame)
      observer.disconnect()
      controls.dispose()
      box.dispose(); shadow.geometry.dispose()
      decorations.forEach(tree => tree.children.forEach(child => {
        if (child instanceof THREE.Mesh) { child.geometry.dispose(); (child.material as THREE.Material).dispose() }
      }))
      ;(shadow.material as THREE.Material).dispose()
      materials.forEach(value => value.dispose())
      renderer.dispose()
    },
  }
}
