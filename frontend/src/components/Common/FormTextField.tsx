import type { Control, FieldPath, FieldValues } from "react-hook-form"

import {
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form"
import { Input } from "@/components/ui/input"

interface FormTextFieldProps<TFieldValues extends FieldValues>
  extends Omit<React.ComponentProps<typeof Input>, "name"> {
  control: Control<TFieldValues>
  /**
   * Field name. Defaults to the label lowercased with spaces replaced by
   * underscores (e.g. "Sort Order" -> "sort_order") when omitted.
   */
  name?: FieldPath<TFieldValues>
  label: string
  required?: boolean
  // Allow data-* attributes (e.g. data-testid) to flow through to the input.
  [dataAttribute: `data-${string}`]: string | undefined
}

export function FormTextField<TFieldValues extends FieldValues>({
  control,
  name,
  label,
  required,
  ...inputProps
}: FormTextFieldProps<TFieldValues>) {
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
            <Input
              aria-invalid={fieldState.invalid}
              required={required}
              {...inputProps}
              {...field}
            />
          </FormControl>
          <FormMessage />
        </FormItem>
      )}
    />
  )
}
