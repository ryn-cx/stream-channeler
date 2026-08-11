// TODO: Validate
import type { Control, FieldPath, FieldValues } from "react-hook-form"

import { Button } from "@/components/ui/button"
import {
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form"
import { Input } from "@/components/ui/input"
import { currentLocalDateTime } from "@/lib/datetime"

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
  /** Show a "Now" button that fills the field with the current local datetime. */
  showNowButton?: boolean
  // Allow data-* attributes (e.g. data-testid) to flow through to the input.
  [dataAttribute: `data-${string}`]: string | undefined
}

// TODO: Validate
export function FormTextField<TFieldValues extends FieldValues>({
  control,
  name,
  label,
  required,
  showNowButton,
  ...inputProps
}: FormTextFieldProps<TFieldValues>) {
  const fieldName =
    name ?? (label.toLowerCase().replace(/ /g, "_") as FieldPath<TFieldValues>)
  return (
    <FormField
      control={control}
      name={fieldName}
      render={({ field, fieldState }) => {
        const input = (
          <FormControl>
            <Input
              aria-invalid={fieldState.invalid}
              required={required}
              {...inputProps}
              {...field}
            />
          </FormControl>
        )
        return (
          <FormItem>
            <FormLabel>
              {label}
              {required && <span className="text-destructive"> *</span>}
            </FormLabel>
            {showNowButton ? (
              <div className="flex gap-2">
                {input}
                <Button
                  type="button"
                  variant="outline"
                  className="shrink-0"
                  onClick={() => field.onChange(currentLocalDateTime())}
                >
                  Now
                </Button>
              </div>
            ) : (
              input
            )}
            <FormMessage />
          </FormItem>
        )
      }}
    />
  )
}
