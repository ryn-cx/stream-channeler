// TODO: Validate
import { Pencil } from "lucide-react"
import { useState } from "react"
import type { ChannelOutput } from "@/client"
import { EditChannelDialog } from "@/components/Channels/EditChannelDialog"
import { TooltipIconButton } from "@/components/Common/TooltipIconButton"

interface EditChannelProps {
  channel: ChannelOutput
}

const EditChannel = ({ channel }: EditChannelProps) => {
  const [open, setOpen] = useState(false)

  return (
    <>
      <TooltipIconButton
        label="Edit Channel"
        icon={<Pencil className="size-4" />}
        onClick={() => setOpen(true)}
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
