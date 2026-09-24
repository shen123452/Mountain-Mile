// Terrain math adapted from summer-checkin (MIT); see NOTICE.md.
export type TileKind = 'forest' | 'moss' | 'water' | 'rock' | 'river' | 'village' | 'waterfall'
export interface TileData { x: number; z: number; height: number; elevation: number; kind: TileKind; unlockOrder: number }
export interface TerrainOptions { seed: string; gridW?: number; gridH?: number }

export function seedNumber(seed: string): number {
  let hash = 2166136261
  for (const char of seed) { hash ^= char.charCodeAt(0); hash = Math.imul(hash, 16777619) }
  return hash >>> 0
}

function mulberry32(seed: number): () => number {
  return () => {
    seed |= 0; seed = seed + 0x6d2b79f5 | 0
    let t = Math.imul(seed ^ seed >>> 15, 1 | seed)
    t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t
    return ((t ^ t >>> 14) >>> 0) / 4294967296
  }
}

function noise(x: number, z: number, phase: number): number {
  return Math.sin(x * 0.37 + phase) * Math.cos(z * 0.41 + phase * 1.3)
}

function hashCell(x: number, z: number, seed: number): number {
  let h = Math.imul(x + 4096, 374761393) ^ Math.imul(z + 4096, 668265263) ^ seed
  h = Math.imul(h ^ h >>> 13, 1274126177)
  return (h ^ h >>> 16) >>> 0
}

export function generateTerrain({ seed, gridW = 17, gridH = 13 }: TerrainOptions): TileData[] {
  if (!Number.isInteger(gridW) || !Number.isInteger(gridH) || gridW < 3 || gridH < 3) throw new Error('Invalid grid size')
  const seedValue = seedNumber(seed)
  const phase = seedValue / 4294967296 * Math.PI * 2
  const halfW = (gridW - 1) / 2
  const halfH = (gridH - 1) / 2
  const cells: Array<{ x: number; z: number }> = []
  for (let row = 0; row < gridH; row++) for (let col = 0; col < gridW; col++) {
    const x = col - halfW, z = row - halfH
    const ex = x / (halfW + 1), ez = z / (halfH + 1)
    if (ex * ex + ez * ez <= 1.05) cells.push({ x, z })
  }
  const shuffled = [...cells]
  const rng = mulberry32(seedValue)
  for (let i = shuffled.length - 1; i > 0; i--) {
    const j = Math.floor(rng() * (i + 1))
    ;[shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]]
  }
  const orders = new Map(shuffled.map((cell, index) => [`${cell.x},${cell.z}`, index + 1]))
  return cells.map(({ x, z }) => {
    const ex = x / (halfW + 1), ez = z / (halfH + 1)
    const distance = Math.hypot(ex, ez)
    const riverCenter = Math.sin(x * 0.22 + phase) * 1.8 + Math.sin(x * 0.13 + 1.5) * 1.1
    const onRiver = Math.abs(z - riverCenter) < 0.56
    const roll = hashCell(x, z, seedValue) % 100
    const kind: TileKind = onRiver ? (roll < 8 ? 'waterfall' : 'river')
      : roll < 5 ? 'water' : roll < 18 ? 'rock' : roll < 36 ? 'moss' : roll < 39 ? 'village' : 'forest'
    const centerPeak = Math.max(0, 1 - distance) * 1.6
    const centerRamp = Math.max(0, 1 - distance * 0.7) * 0.4
    const surface = centerPeak + centerRamp + noise(x, z, phase) * 0.4
      + noise(x, z, phase + 5) * 0.35 + Math.sin(x * 0.25 + z * 0.3) * 0.2
      + Math.abs(noise(x, z, phase + 10)) * 0.12 - distance * 0.3
    const elevation = Math.round((surface - (kind === 'water' ? 0.6 : onRiver ? 0.35 : 0)) * 100) / 100
    const height = Math.round((0.25 + (hashCell(x, z, seedValue + 1) % 7) * 0.07 + (1 - distance) * 0.3) * 100) / 100
    return { x, z, height, elevation, kind, unlockOrder: orders.get(`${x},${z}`)! }
  })
}

export function unlockedTileCount(total: number, initial = 20, added = 0): number {
  return Math.max(0, Math.min(total, initial + added))
}
