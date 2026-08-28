// TODO: Validate
import { Pencil } from "lucide-react"
import { useState } from "react"

import { TooltipIconButton } from "@/components/Common/TooltipIconButton"
import EditEpisode from "@/components/Episodes/Edit"
import useAuth from "@/hooks/useAuth"
import { useEpisode } from "@/hooks/useEntities"

// TODO: Validate
/**
 * The episode window, opened by id.
 *
 * The row's own columns are read only for an admin, since that read is an admin
 * request and a reader who may not edit is never shown them anyway. Everything
 * else the window holds is reached from the id alone, so it opens at once for
 * anybody.
 */
export function EditEpisodeById({
  episodeId,
  label = "Edit this episode",
  open,
  onOpenChange,
}: {
  episodeId: string
  label?: string
  open?: boolean
  onOpenChange?: (open: boolean) => void
}) {
  const [isOpenHere, setIsOpenHere] = useState(false)
  const isOpen = open ?? isOpenHere
  const setIsOpen = onOpenChange ?? setIsOpenHere
  const { user } = useAuth()
  const isAdmin = Boolean(user?.is_superuser)
  const { data: fields } = useEpisode(isAdmin && isOpen ? episodeId : undefined)
  const episode = isAdmin ? fields : { id: episodeId }

  return (
    <>
      {open === undefined ? (
        <TooltipIconButton
          label={label}
          icon={<Pencil />}
          size="icon-sm"
          onClick={() => setIsOpen(true)}
        />
      ) : null}
      {isOpen && episode ? (
        <EditEpisode episode={episode} open onOpenChange={setIsOpen} />
      ) : null}
    </>
  )
}
