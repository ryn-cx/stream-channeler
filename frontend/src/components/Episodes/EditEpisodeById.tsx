// TODO: Validate
import { Pencil } from "lucide-react"

import { TooltipIconButton } from "@/components/Common/TooltipIconButton"
import { useOpenMedia } from "@/hooks/useOpenMedia"

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
}: {
  episodeId: string
  label?: string
}) {
  const openMedia = useOpenMedia()
  return (
    <TooltipIconButton
      label={label}
      icon={<Pencil />}
      size="icon-sm"
      onClick={() => openMedia({ kind: "episode", episode: { id: episodeId } })}
    />
  )
}
