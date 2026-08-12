// TODO: Validate
import { Link } from "@tanstack/react-router"

import type { ChannelListOutput, ChannelOutput, Visibility } from "@/client"
import useAuth from "@/hooks/useAuth"
import { cn } from "@/lib/utils"

const VISIBILITY_LABELS: Record<Visibility, string> = {
  public: "Public",
  unlisted: "Unlisted",
  private: "Private",
}

// Only the fields the credit line needs, so both the list and detail shapes fit.
export type CreditedChannel = Pick<
  ChannelListOutput | ChannelOutput,
  "visibility" | "anonymous" | "user_id" | "username"
>

interface ChannelCreatedByProps {
  channel: CreditedChannel
  className?: string
}

// TODO: Validate
export function ChannelCreatedBy({
  channel,
  className,
}: ChannelCreatedByProps) {
  const { user } = useAuth()

  const paragraphClass = cn("text-sm text-muted-foreground", className)
  const prefix = `${VISIBILITY_LABELS[channel.visibility]} channel`

  if (channel.anonymous) {
    return <p className={paragraphClass}>{prefix} by Anonymous</p>
  }

  // The API withholds the username of a channel the viewer owns, so their own
  // name from the session fills it in.
  const username =
    channel.username ??
    (channel.user_id === user?.id ? (user?.username ?? null) : null)

  if (!channel.user_id || !username) {
    return <p className={paragraphClass}>{prefix}</p>
  }

  return (
    <p className={paragraphClass}>
      {prefix} by{" "}
      <Link
        to="/users/$userId/channels"
        params={{ userId: channel.user_id }}
        className="underline hover:text-foreground"
      >
        {username}
      </Link>
    </p>
  )
}
