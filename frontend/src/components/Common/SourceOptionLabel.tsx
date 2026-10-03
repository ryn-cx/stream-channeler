// TODO: Validate
import { Globe } from "lucide-react"
import { Favicon } from "@/components/Common/Favicon"

interface SourceOptionLabelProps {
  name: string
  faviconUrl?: string | null
}

// TODO: Validate
export function SourceOptionLabel({
  name,
  faviconUrl,
}: SourceOptionLabelProps) {
  return (
    <span className="flex items-center gap-2">
      {faviconUrl ? (
        <Favicon
          src={faviconUrl}
          label={name}
          className="rounded-sm"
          tooltip={false}
        />
      ) : (
        <Globe className="size-4 shrink-0 text-muted-foreground" />
      )}
      {name}
    </span>
  )
}
