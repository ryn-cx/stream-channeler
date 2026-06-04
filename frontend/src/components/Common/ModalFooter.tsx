import { Button } from "@/components/ui/button"
import { DialogClose, DialogFooter } from "@/components/ui/dialog"
import type { ButtonProps } from "@/components/ui/loading-button"
import { LoadingButton } from "@/components/ui/loading-button"
import { cn } from "@/lib/utils"

interface ModalFooterProps {
  /** Disables both buttons and shows a spinner on submit while a request runs. */
  isPending?: boolean
  cancelLabel?: string
  submitLabel?: string
  /** Variant of the submit button, e.g. `destructive` for delete dialogs. */
  submitVariant?: ButtonProps["variant"]
  className?: string
}

/**
 * Shared modal footer: an outline Cancel button that closes the dialog and a
 * submit button that drives the surrounding form. Keeps the Cancel/Save layout
 * and pending behavior identical across every modal.
 */
export function ModalFooter({
  isPending = false,
  cancelLabel = "Cancel",
  submitLabel = "Save",
  submitVariant,
  className,
}: ModalFooterProps) {
  return (
    <DialogFooter className={cn(className)}>
      <DialogClose asChild>
        <Button variant="outline" disabled={isPending}>
          {cancelLabel}
        </Button>
      </DialogClose>
      <LoadingButton type="submit" variant={submitVariant} loading={isPending}>
        {submitLabel}
      </LoadingButton>
    </DialogFooter>
  )
}
