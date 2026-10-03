// TODO: Validate
import type { ComponentProps } from "react"

import type { Visibility } from "@/client"
import { EpisodeFilters } from "@/components/Channels/ChannelDetail/EpisodeFilters"
import { parseOrderConfig } from "@/lib/channelOrder"

interface EditOrderConfigDialogProps {
  order: {
    id: string
    name?: string | null
    description?: string | null
    visibility: Visibility
    anonymous?: boolean
    icon?: string | null
    score?: number
    config: string
  }
  open: boolean
  onOpenChange: (open: boolean) => void
}

// TODO: Validate
export function EditOrderConfigDialog({
  order,
  open,
  onOpenChange,
}: EditOrderConfigDialogProps) {
  const config = parseOrderConfig(order.config) as Record<string, unknown>
  const randomSeed = config.randomSeed

  return (
    <EpisodeFilters
      filterParams={
        config as ComponentProps<typeof EpisodeFilters>["filterParams"]
      }
      randomSeed={typeof randomSeed === "number" ? randomSeed : undefined}
      orderEdit={{
        order,
        onSaved: () => onOpenChange(false),
      }}
      open={open}
      onOpenChange={onOpenChange}
    />
  )
}
