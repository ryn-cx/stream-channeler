// TODO: Validate
import { Search } from "lucide-react"

import { Input } from "@/components/ui/input"

// TODO: Validate
export function ChannelSearchInput({
  value,
  onValueChange,
}: {
  value: string
  onValueChange: (value: string) => void
}) {
  return (
    <div className="relative max-w-sm">
      <Search className="pointer-events-none absolute left-2.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
      <Input
        value={value}
        onChange={(event) => onValueChange(event.target.value)}
        placeholder="Search channels"
        className="pl-8"
      />
    </div>
  )
}
