// TODO: Validate
import { Check, Move } from "lucide-react"

import {
  type TriggerVariant,
  VariantTrigger,
} from "@/components/Common/VariantTrigger"

interface EditOrderButtonProps {
  editOrder: boolean
  onToggle: () => void
  variant?: TriggerVariant
}

export function EditOrderButton({
  editOrder,
  onToggle,
  variant = "button",
}: EditOrderButtonProps) {
  return (
    <VariantTrigger
      variant={variant}
      icon={editOrder ? Check : Move}
      label={editOrder ? "Done" : "Edit Order"}
      title={editOrder ? "Finish reordering" : "Reorder episodes"}
      iconTitle={editOrder ? "Finish reordering" : "Reorder episodes"}
      onClick={onToggle}
      onSelect={onToggle}
    />
  )
}
