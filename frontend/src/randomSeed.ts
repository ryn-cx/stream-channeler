// TODO: Validate
const SEED_KEY_PREFIX = "random-seed-"

// TODO: Validate
export function getSeedStorageKey(channelId: string) {
  return `${SEED_KEY_PREFIX}${channelId}`
}

// TODO: Validate
export function getStoredSeed(channelId: string): number | undefined {
  const stored = localStorage.getItem(getSeedStorageKey(channelId))
  if (stored === null) return undefined
  try {
    const parsed = JSON.parse(stored)
    if (
      typeof parsed?.seed === "number" &&
      typeof parsed?.createdAt === "number" &&
      Date.now() - parsed.createdAt < 60 * 60 * 1000
    ) {
      return parsed.seed
    }
  } catch {
    localStorage.removeItem(getSeedStorageKey(channelId))
  }
  return undefined
}

// TODO: Validate
export function storeSeed(channelId: string, seed: number): void {
  try {
    localStorage.setItem(
      getSeedStorageKey(channelId),
      JSON.stringify({ seed, createdAt: Date.now() }),
    )
  } catch {
    localStorage.removeItem(getSeedStorageKey(channelId))
  }
}

// TODO: Validate
export function generateSeed(): number {
  return Math.floor(Math.random() * 2 ** 31)
}

const seedsForThisLoad = new Map<string, number>()

// TODO: Validate
function isPageReload(): boolean {
  const navigation = performance.getEntriesByType("navigation")[0] as
    | PerformanceNavigationTiming
    | undefined
  return navigation?.type === "reload"
}

// TODO: Validate
export function getSeedForThisLoad(channelId: string): number {
  const alreadyChosen = seedsForThisLoad.get(channelId)
  if (alreadyChosen !== undefined) return alreadyChosen
  const storedSeed = isPageReload() ? undefined : getStoredSeed(channelId)
  const seed = storedSeed ?? generateSeed()
  if (storedSeed === undefined) storeSeed(channelId, seed)
  seedsForThisLoad.set(channelId, seed)
  return seed
}
