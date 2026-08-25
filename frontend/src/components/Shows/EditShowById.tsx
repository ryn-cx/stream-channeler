// TODO: Validate
import { Pencil } from "lucide-react"
import { useState } from "react"

import { TooltipIconButton } from "@/components/Common/TooltipIconButton"
import EditShow from "@/components/Shows/Edit"
import { useShow } from "@/hooks/useEntities"

// TODO: Validate
export function EditShowById({
  showId,
  label = "Edit this show",
}: {
  showId: string
  label?: string
}) {
  const [isOpen, setIsOpen] = useState(false)
  const { data: show } = useShow(isOpen ? showId : undefined)
  return (
    <>
      <TooltipIconButton
        label={label}
        icon={<Pencil />}
        size="icon-sm"
        onClick={() => setIsOpen(true)}
      />
      {isOpen && show ? (
        <EditShow show={show} open onOpenChange={setIsOpen} />
      ) : null}
    </>
  )
}
