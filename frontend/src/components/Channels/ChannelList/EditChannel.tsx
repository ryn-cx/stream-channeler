// TODO: Validate
import { Link } from "@tanstack/react-router"
import { Pencil } from "lucide-react"
import type { ChannelOutput } from "@/client"
import { Button } from "@/components/ui/button"

interface EditChannelProps {
  channel: ChannelOutput
}

const EditChannel = ({ channel }: EditChannelProps) => {
  return (
    <Button asChild variant="ghost" size="icon" title="Edit channel">
      <Link to="/onboarding/$channelId/name" params={{ channelId: channel.id }}>
        <Pencil className="size-4" />
      </Link>
    </Button>
  )
}

export default EditChannel
