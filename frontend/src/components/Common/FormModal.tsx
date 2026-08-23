// TODO: Validate
import type { ReactNode } from "react"
import type { FieldValues, SubmitHandler, UseFormReturn } from "react-hook-form"

import { ModalContent, type ModalSize } from "@/components/Common/ModalContent"
import { ModalFooter } from "@/components/Common/ModalFooter"
import {
  Dialog,
  DialogBody,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Form } from "@/components/ui/form"

interface FormModalProps<
  TFieldValues extends FieldValues,
  TContext,
  TTransformedValues extends FieldValues,
> {
  open: boolean
  onOpenChange: (open: boolean) => void
  /**
   * The element that opens the dialog. Provide the full trigger yourself —
   * e.g. `<DialogTrigger asChild>...</DialogTrigger>`, a `<TooltipIconButton>`
   * with an `onClick` that sets `open`, or any button — so each modal keeps its
   * own trigger styling.
   */
  trigger: ReactNode
  title: ReactNode
  description?: ReactNode
  form: UseFormReturn<TFieldValues, TContext, TTransformedValues>
  onSubmit: SubmitHandler<TTransformedValues>
  isPending?: boolean
  submitLabel?: string
  size?: ModalSize
  footerStart?: ReactNode
  /** The form fields rendered inside the standard `grid gap-4 py-4` body. */
  children: ReactNode
}

// TODO: Validate
/**
 * Standard form-in-a-dialog shell: wires up the dialog, scrollable content,
 * header, the react-hook-form `<Form>` provider, the field grid, and the
 * Cancel/Save footer. Callers only supply the trigger, copy, form, submit
 * handler, and the fields themselves.
 */
export function FormModal<
  TFieldValues extends FieldValues,
  TContext,
  TTransformedValues extends FieldValues,
>({
  open,
  onOpenChange,
  trigger,
  title,
  description,
  form,
  onSubmit,
  isPending,
  submitLabel,
  size,
  footerStart,
  children,
}: FormModalProps<TFieldValues, TContext, TTransformedValues>) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      {trigger}
      <ModalContent
        size={size}
        className="max-h-[calc(100dvh-2rem)] overflow-y-hidden"
      >
        <Form {...form}>
          <form
            onSubmit={form.handleSubmit(onSubmit)}
            className="flex min-h-0 flex-1 flex-col"
          >
            <DialogHeader>
              <DialogTitle>{title}</DialogTitle>
              {description ? (
                <DialogDescription>{description}</DialogDescription>
              ) : null}
            </DialogHeader>
            <DialogBody className="max-h-none min-h-0 flex-1">
              <div className="grid gap-4 py-4">{children}</div>
            </DialogBody>
            <ModalFooter
              isPending={isPending}
              submitLabel={submitLabel}
              start={footerStart}
            />
          </form>
        </Form>
      </ModalContent>
    </Dialog>
  )
}
