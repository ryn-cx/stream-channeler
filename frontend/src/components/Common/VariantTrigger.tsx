// TODO: Validate
import type { LucideIcon } from "lucide-react"
import { forwardRef, type Ref } from "react"

import { Button } from "@/components/ui/button"
import { DropdownMenuItem } from "@/components/ui/dropdown-menu"

export type TriggerVariant = "button" | "menu" | "icon"

interface VariantTriggerProps
  extends Omit<React.HTMLAttributes<HTMLElement>, "onSelect"> {
  variant: TriggerVariant
  icon: LucideIcon
  /** Used in place of `icon` when `variant === "icon"`. Defaults to `icon`. */
  iconVariantIcon?: LucideIcon
  /** Label shown for `button` (and `menu`, unless `menuLabel` is set). */
  label: string
  /** Overrides the label for the `menu` variant. */
  menuLabel?: string
  /** title attribute for the `icon` variant. */
  iconTitle?: string
  onSelect?: (event: Event) => void
  disabled?: boolean
}

export const VariantTrigger = forwardRef<HTMLElement, VariantTriggerProps>(
  function VariantTrigger(
    {
      variant,
      icon: Icon,
      iconVariantIcon,
      label,
      menuLabel,
      iconTitle,
      onSelect,
      ...rest
    },
    ref,
  ) {
    if (variant === "menu") {
      return (
        <DropdownMenuItem
          ref={ref as Ref<HTMLDivElement>}
          onSelect={onSelect ?? ((event) => event.preventDefault())}
          {...rest}
        >
          <Icon />
          {menuLabel ?? label}
        </DropdownMenuItem>
      )
    }
    if (variant === "icon") {
      const IconComponent = iconVariantIcon ?? Icon
      return (
        <Button
          ref={ref as Ref<HTMLButtonElement>}
          variant="ghost"
          size="icon"
          title={iconTitle}
          {...rest}
        >
          <IconComponent />
        </Button>
      )
    }
    return (
      <Button
        ref={ref as Ref<HTMLButtonElement>}
        className="mt-2 mb-4"
        {...rest}
      >
        <Icon />
        {label}
      </Button>
    )
  },
)
