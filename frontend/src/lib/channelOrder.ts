// TODO: Validate
import type { SortKeyInput } from "@/client"

/** The sorting-only configuration stored in a `ChannelOrder.config` blob. */
export interface ChannelOrderConfig {
  sortBy?: SortKeyInput[]
  randomSeed?: number
}

export function parseOrderConfig(config: string): ChannelOrderConfig {
  try {
    return JSON.parse(config) as ChannelOrderConfig
  } catch {
    return {}
  }
}

export function serializeOrderConfig(config: ChannelOrderConfig): string {
  return JSON.stringify(config)
}

export function orderSortStepCount(config: string): number {
  return parseOrderConfig(config).sortBy?.length ?? 0
}
