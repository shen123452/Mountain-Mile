export type PaletteName = 'jade' | 'azurite' | 'ochre' | 'pale'
export interface IslandPalette { top: string; side: string; moss: string; rock: string; water: string; tree: string; accent: string; sky: string }

export const palettes: Record<PaletteName, IslandPalette> = {
  jade: { top: '#6a9d72', side: '#315e4c', moss: '#9db77b', rock: '#8c9a84', water: '#4c929a', tree: '#245b4b', accent: '#c49b62', sky: '#e8eee4' },
  azurite: { top: '#739c9a', side: '#305d68', moss: '#9cb7a2', rock: '#859ba3', water: '#357b9a', tree: '#285d61', accent: '#c7a06b', sky: '#e6eef0' },
  ochre: { top: '#a69c6b', side: '#74694e', moss: '#b9aa77', rock: '#978875', water: '#6d9b96', tree: '#576b4c', accent: '#aa704e', sky: '#f1ece0' },
  pale: { top: '#a5ba9d', side: '#698675', moss: '#cad2aa', rock: '#aeb5aa', water: '#92b9b9', tree: '#668875', accent: '#b6956e', sky: '#f4f4e9' },
}
