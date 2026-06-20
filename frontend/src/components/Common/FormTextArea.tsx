// TODO: Validate
import type { Control, FieldPath, FieldValues } from "react-hook-form"

import {
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form"
import { Textarea } from "@/components/ui/textarea"

interface FormTextAreaProps<TFieldValues extends FieldValues>
  extends Omit<React.ComponentProps<typeof Textarea>, "name"> {
  control: Control<TFieldValues>
  /**
   * Field name. Defaults to the label lowercased with spaces replaced by
   * underscores (e.g. "Sort Order" -> "sort_order") when omitted.
   */
  name?: FieldPath<TFieldValues>
  label: string
  required?: boolean
}

export function FormTextArea<TFieldValues extends FieldValues>({
  control,
  name,
  label,
  required,
  ...textareaProps
}: FormTextAreaProps<TFieldValues>) {
  const fieldName =
    name ?? (label.toLowerCase().replace(/ /g, "_") as FieldPath<TFieldValues>)
  return (
    <FormField
      control={control}
      name={fieldName}
      render={({ field, fieldState }) => (
        <FormItem>
          <FormLabel>
            {label}
            {required && <span className="text-destructive"> *</span>}
          </FormLabel>
          <FormControl>
            <Textarea
              aria-invalid={fieldState.invalid}
              required={required}
              {...textareaProps}
              {...field}
            />
          </FormControl>
          <FormMessage />
        </FormItem>
      )}
    />
  )
}
