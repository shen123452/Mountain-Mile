import { describe, expect, it } from 'vitest'
import { generateTerrain, unlockedTileCount } from './terrain'

describe('generateTerrain', () => {
  it('is deterministic for a goal seed and has a complete unlock order', () => {
    const first = generateTerrain({ seed: 'high-math' })
    expect(generateTerrain({ seed: 'high-math' })).toEqual(first)
    expect({
      count: first.length,
      sample: first.filter((_, index) => index % 17 === 0),
      kinds: first.reduce<Record<string, number>>((counts, tile) => {
        counts[tile.kind] = (counts[tile.kind] ?? 0) + 1
        return counts
      }, {}),
    }).toMatchSnapshot()
    expect(new Set(first.map(tile => tile.unlockOrder)).size).toBe(first.length)
    expect(Math.min(...first.map(tile => tile.unlockOrder))).toBe(1)
    expect(Math.max(...first.map(tile => tile.unlockOrder))).toBe(first.length)
  })

  it('varies by seed and clamps visible tiles', () => {
    const first = generateTerrain({ seed: 'high-math' })
    const second = generateTerrain({ seed: 'english' })
    expect(second).not.toEqual(first)
    expect(unlockedTileCount(first.length, 20, 5)).toBe(25)
    expect(unlockedTileCount(first.length, 20, first.length)).toBe(first.length)
  })
})
