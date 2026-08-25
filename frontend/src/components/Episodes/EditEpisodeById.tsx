// TODO: Validate
import { Pencil } from "lucide-react"
import { useState } from "react"

import { TooltipIconButton } from "@/components/Common/TooltipIconButton"
import EditEpisode from "@/components/Episodes/Edit"
import { useEpisode } from "@/hooks/useEntities"

// TODO: Validate
export function EditEpisodeById({
  episodeId,
  label = "Edit this episode",
}: {
  episodeId: string
  label?: string
}) {
  const [isOpen, setIsOpen] = useState(false)
  const { data: episode } = useEpisode(isOpen ? episodeId : undefined)
  return (
    <>
      <TooltipIconButton
        label={label}
        icon={<Pencil />}
        size="icon-sm"
        onClick={() => setIsOpen(true)}
      />
      {isOpen && episode ? (
        <EditEpisode episode={episode} open onOpenChange={setIsOpen} />
      ) : null}
    </>
  )
}
