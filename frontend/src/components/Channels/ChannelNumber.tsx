// TODO: Validate
import { cn } from "@/lib/utils"

interface ChannelNumberProps {
  channelNumber?: number | null
  customChannelNumber?: number | null
  className?: string
}

// TODO: Validate
export function ChannelNumber({
  channelNumber,
  customChannelNumber,
  className,
}: ChannelNumberProps) {
  return (
    <span className={cn("text-muted-foreground tabular-nums", className)}>
      {customChannelNumber ?? channelNumber ?? "—"}
    </span>
  )
}
