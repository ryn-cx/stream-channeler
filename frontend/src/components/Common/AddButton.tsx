// TODO: Validate
import { Plus } from "lucide-react"

import { Button } from "@/components/ui/button"

// TODO: Validate
export function AddButton({
  className,
  children,
  ...props
}: React.ComponentProps<typeof Button>) {
  return (
    <Button className={className} {...props}>
      <Plus className="mr-2" />
      {children}
    </Button>
  )
}
