// TODO: Validate
import { Pencil } from "lucide-react"
import { useState } from "react"
import type { ChannelOutput } from "@/client"
import { EditChannelDialog } from "@/components/Channels/EditChannelDialog"
import { Button } from "@/components/ui/button"

interface EditChannelProps {
  channel: ChannelOutput
}

const EditChannel = ({ channel }: EditChannelProps) => {
  const [open, setOpen] = useState(false)

  return (
    <>
      <Button
        variant="ghost"
        size="icon"
        title="Edit Channel"
        onClick={() => setOpen(true)}
      >
        <Pencil className="size-4" />
      </Button>
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
