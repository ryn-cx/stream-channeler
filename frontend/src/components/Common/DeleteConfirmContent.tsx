// TODO: Validate
import type { ReactNode } from "react"

import { Button } from "@/components/ui/button"
import {
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { LoadingButton } from "@/components/ui/loading-button"

interface DeleteConfirmContentProps {
  title: string
  description: ReactNode
  isPending: boolean
  onSubmit: () => void
  cancelLabel?: string
  confirmLabel?: string
}

export function DeleteConfirmContent({
  title,
  description,
  isPending,
  onSubmit,
  cancelLabel = "Cancel",
  confirmLabel = "Delete",
}: DeleteConfirmContentProps) {
  return (
    <DialogContent className="sm:max-w-md">
      <form
        onSubmit={(event) => {
          event.preventDefault()
          onSubmit()
        }}
      >
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
          <DialogDescription>{description}</DialogDescription>
        </DialogHeader>

        <DialogFooter className="mt-4">
          <DialogClose asChild>
            <Button variant="outline" disabled={isPending}>
              {cancelLabel}
            </Button>
          </DialogClose>
          <LoadingButton
            variant="destructive"
            type="submit"
            loading={isPending}
          >
            {confirmLabel}
          </LoadingButton>
        </DialogFooter>
      </form>
    </DialogContent>
  )
}
