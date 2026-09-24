import * as THREE from 'three'
import type { IslandPalette } from './palettes'

export function createTree(palette: IslandPalette): THREE.Group {
  const group = new THREE.Group()
  const stem = new THREE.Mesh(new THREE.CylinderGeometry(0.045, 0.07, 0.28, 5), new THREE.MeshStandardMaterial({ color: '#735b42', roughness: 1 }))
  stem.position.y = 0.18
  const leaves = new THREE.Mesh(new THREE.ConeGeometry(0.27, 0.72, 6), new THREE.MeshStandardMaterial({ color: palette.tree, flatShading: true, roughness: 1 }))
  leaves.position.y = 0.62
  group.add(stem, leaves)
  return group
}
