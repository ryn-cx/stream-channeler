// TODO: Validate
import { Check, Move } from "lucide-react"

import { Button } from "@/components/ui/button"

interface EditOrderButtonProps {
  editOrder: boolean
  onToggle: () => void
}

export function EditOrderButton({ editOrder, onToggle }: EditOrderButtonProps) {
  return (
    <Button
      onClick={onToggle}
      title={editOrder ? "Finish reordering" : "Reorder episodes"}
      className="mt-2 mb-4"
    >
      {editOrder ? <Check /> : <Move />}
      {editOrder ? "Done" : "Edit Order"}
    </Button>
  )
}
