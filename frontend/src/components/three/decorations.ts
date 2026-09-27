import * as THREE from 'three'
import type { IslandPalette } from './palettes'

export function createTree(palette: IslandPalette): THREE.Group {
  const group = new THREE.Group()
  group.userData.decoration = true
  const stem = new THREE.Mesh(new THREE.CylinderGeometry(0.045, 0.07, 0.28, 5), new THREE.MeshStandardMaterial({ color: '#735b42', roughness: 1 }))
  stem.position.y = 0.18
  const crown = new THREE.Group()
  crown.position.y = 0.42
  crown.userData.decoration = true
  const colors = [palette.tree, palette.tree, palette.tree]
  const positions: [number, number, number][] = [[0, 0.05, 0], [-0.12, -0.01, 0.02], [0.12, 0, -0.02]]
  positions.forEach(([x, y, z], index) => {
    const leaves = new THREE.Mesh(new THREE.IcosahedronGeometry(index === 0 ? 0.19 : 0.14, 0), new THREE.MeshStandardMaterial({ color: colors[index], flatShading: true, roughness: 0.94 }))
    leaves.position.set(x, y, z)
    leaves.userData.role = 'tree-leaf'
    crown.add(leaves)
  })
  group.add(stem, crown)
  return group
}

export function createRock(palette: IslandPalette): THREE.Group {
  const group = new THREE.Group()
  group.userData.decoration = true
  const rock = new THREE.Mesh(new THREE.DodecahedronGeometry(0.16, 0), new THREE.MeshStandardMaterial({ color: palette.rock, flatShading: true, roughness: 1 }))
  rock.scale.set(1, 0.72, 0.82)
  rock.position.y = 0.1
  group.add(rock)
  return group
}

export function createPond(palette: IslandPalette): THREE.Group {
  const group = new THREE.Group()
  group.userData.decoration = true
  const water = new THREE.Mesh(new THREE.CircleGeometry(0.16, 10), new THREE.MeshStandardMaterial({ color: palette.water, roughness: 0.2, transparent: true, opacity: 0.9 }))
  water.rotation.x = -Math.PI / 2
  water.position.y = 0.02
  group.add(water)
  return group
}
