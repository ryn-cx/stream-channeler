// TODO: Validate
import type { ChannelOutput } from "@/client"

// TODO: Validate
export function readChannelDetails(
  channelId: string,
): ChannelOutput | undefined {
  const stored = localStorage.getItem(`channel-details:${channelId}`)
  if (stored === null) return undefined
  try {
    const parsed = JSON.parse(stored) as Partial<ChannelOutput>
    if (typeof parsed.id === "string") return parsed as ChannelOutput
  } catch {
    localStorage.removeItem(`channel-details:${channelId}`)
  }
  return undefined
}

// TODO: Validate
function trimStoredChannelDetails(keepChannelId: string): void {
  const stored = localStorage.getItem("channel-details-order")
  const previous: string[] = stored === null ? [] : JSON.parse(stored)
  const next = [keepChannelId, ...previous.filter((id) => id !== keepChannelId)]
  for (const id of next.slice(20)) {
    localStorage.removeItem(`channel-details:${id}`)
  }
  localStorage.setItem(
    "channel-details-order",
    JSON.stringify(next.slice(0, 20)),
  )
}

// TODO: Validate
export function writeChannelDetails(channel: ChannelOutput): void {
  try {
    localStorage.setItem(
      `channel-details:${channel.id}`,
      JSON.stringify(channel),
    )
    trimStoredChannelDetails(channel.id)
  } catch {
    localStorage.removeItem(`channel-details:${channel.id}`)
  }
}
