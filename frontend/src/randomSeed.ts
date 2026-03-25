// TODO: Validate
const SEED_KEY_PREFIX = "random-seed-"

export function getSeedStorageKey(channelId: string) {
  return `${SEED_KEY_PREFIX}${channelId}`
}

export function getStoredSeed(channelId: string): number | undefined {
  const stored = localStorage.getItem(getSeedStorageKey(channelId))
  if (stored === null) return undefined
  const parsed = parseInt(stored, 10)
  return Number.isNaN(parsed) ? undefined : parsed
}

export function storeSeed(channelId: string, seed: number): void {
  localStorage.setItem(getSeedStorageKey(channelId), String(seed))
}

export function generateSeed(): number {
  return Math.floor(Math.random() * 2 ** 31)
}

export function getOrCreateStoredSeed(channelId: string): number {
  const existing = getStoredSeed(channelId)
  if (existing !== undefined) return existing
  const seed = generateSeed()
  storeSeed(channelId, seed)
  return seed
}
