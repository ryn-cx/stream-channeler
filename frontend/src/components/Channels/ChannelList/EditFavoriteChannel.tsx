// TODO: Validate
import { SlidersHorizontal } from "lucide-react"
import { useState } from "react"
import type { ChannelListOutput } from "@/client"
import { EditFavoriteChannelDialog } from "@/components/Channels/EditFavoriteChannelDialog"
import { TooltipIconButton } from "@/components/Common/TooltipIconButton"

interface EditFavoriteChannelProps {
  channel: ChannelListOutput
}

// TODO: Validate
const EditFavoriteChannel = ({ channel }: EditFavoriteChannelProps) => {
  const [open, setOpen] = useState(false)

  return (
    <>
      <TooltipIconButton
        label="Personalize Channel"
        icon={<SlidersHorizontal className="size-4" />}
        onClick={() => setOpen(true)}
      />
      {open && (
        <EditFavoriteChannelDialog
          channel={channel}
          open={open}
          onOpenChange={setOpen}
        />
      )}
    </>
  )
}

export default EditFavoriteChannel
