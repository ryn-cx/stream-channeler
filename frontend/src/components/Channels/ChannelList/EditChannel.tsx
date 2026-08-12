// TODO: Validate
import { Pencil } from "lucide-react"
import { useState } from "react"
import type { ChannelOutput } from "@/client"
import { EditChannelDialog } from "@/components/Channels/EditChannelDialog"
import { TooltipIconButton } from "@/components/Common/TooltipIconButton"

interface EditChannelProps {
  channel: ChannelOutput
  showLabel?: boolean
}

// TODO: Validate
const EditChannel = ({ channel, showLabel }: EditChannelProps) => {
  const [open, setOpen] = useState(false)

  return (
    <>
      <TooltipIconButton
        label="Edit channel"
        icon={<Pencil className="size-4" />}
        onClick={() => setOpen(true)}
        showLabel={showLabel}
      />
      {open && (
        <EditChannelDialog
          channel={channel}
          open={open}
          onOpenChange={setOpen}
        />
      )}
    </>
  )
}

export default EditChannel
