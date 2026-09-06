// TODO: Validate
import { Pencil } from "lucide-react"
import { useState } from "react"

import { TooltipIconButton } from "@/components/Common/TooltipIconButton"
import EditTitle from "@/components/Titles/Edit"
import { useTitle } from "@/hooks/useEntities"

// TODO: Validate
export function EditTitleById({
  titleId,
  label = "Edit this title",
}: {
  titleId: string
  label?: string
}) {
  const [isOpen, setIsOpen] = useState(false)
  const { data: title } = useTitle(isOpen ? titleId : undefined)
  return (
    <>
      <TooltipIconButton
        label={label}
        icon={<Pencil />}
        size="icon-sm"
        onClick={() => setIsOpen(true)}
      />
      {isOpen && title ? (
        <EditTitle title={title} open onOpenChange={setIsOpen} />
      ) : null}
    </>
  )
}
