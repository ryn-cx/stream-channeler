// TODO: Validate
import { Pencil } from "lucide-react"
import { useState } from "react"

import type { ChannelListOutput } from "@/client"
import { EditChannelDialog } from "@/components/Channels/EditChannelDialog"
import { Button } from "@/components/ui/button"

export function ChannelActions({ channel }: { channel: ChannelListOutput }) {
  const [isEditing, setIsEditing] = useState(false)

  return (
    <div className="flex justify-end gap-2">
      <Button
        variant="outline"
        size="icon-sm"
        onClick={() => setIsEditing(true)}
      >
        <Pencil />
      </Button>
      {isEditing && (
        <EditChannelDialog
          channel={channel}
          open={isEditing}
          onOpenChange={setIsEditing}
        />
      )}
    </div>
  )
}
