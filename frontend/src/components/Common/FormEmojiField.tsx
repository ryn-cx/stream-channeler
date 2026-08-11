// TODO: Validate
import type { Control, FieldPath, FieldValues } from "react-hook-form"

import { EmojiPicker } from "@/components/Common/EmojiPicker"
import {
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form"

interface FormEmojiFieldProps<TFieldValues extends FieldValues> {
  control: Control<TFieldValues>
  name: FieldPath<TFieldValues>
  label: string
}

// TODO: Validate
export function FormEmojiField<TFieldValues extends FieldValues>({
  control,
  name,
  label,
}: FormEmojiFieldProps<TFieldValues>) {
  return (
    <FormField
      control={control}
      name={name}
      render={({ field }) => (
        <FormItem>
          <FormLabel>{label}</FormLabel>
          <FormControl>
            <EmojiPicker
              value={field.value || null}
              onChange={(emoji) => field.onChange(emoji ?? "")}
            />
          </FormControl>
          <FormMessage />
        </FormItem>
      )}
    />
  )
}
