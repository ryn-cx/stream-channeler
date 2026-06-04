import { Plus } from "lucide-react"

import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"

export function AddButton({
  className,
  children,
  ...props
}: React.ComponentProps<typeof Button>) {
  return (
    <Button className={cn("my-4", className)} {...props}>
      <Plus className="mr-2" />
      {children}
    </Button>
  )
}
