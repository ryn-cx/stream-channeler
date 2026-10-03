// TODO: Validate
import type { Control, FieldPath, FieldValues } from "react-hook-form"

import { Checkbox } from "@/components/ui/checkbox"
import {
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form"

interface FormCheckboxFieldProps<TFieldValues extends FieldValues> {
  control: Control<TFieldValues>
  /**
   * Field name. Defaults to the label lowercased with spaces replaced by
   * underscores, the way `FormTextField` derives it.
   */
  name?: FieldPath<TFieldValues>
  label: string
}

// TODO: Validate
/** A `FormTextField` for the columns that hold a yes or a no. */
export function FormCheckboxField<TFieldValues extends FieldValues>({
  control,
  name,
  label,
}: FormCheckboxFieldProps<TFieldValues>) {
  const fieldName =
    name ?? (label.toLowerCase().replace(/ /g, "_") as FieldPath<TFieldValues>)
  return (
    <FormField
      control={control}
      name={fieldName}
      render={({ field }) => (
        <FormItem className="flex items-center gap-3 space-y-0">
          <FormControl>
            <Checkbox checked={field.value} onCheckedChange={field.onChange} />
          </FormControl>
          <FormLabel className="font-normal">{label}</FormLabel>
          <FormMessage />
        </FormItem>
      )}
    />
  )
}
