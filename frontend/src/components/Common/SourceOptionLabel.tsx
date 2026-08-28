// TODO: Validate
import { Globe } from "lucide-react"

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
        <img
          referrerPolicy="no-referrer"
          src={faviconUrl}
          alt=""
          className="size-4 shrink-0 rounded-sm"
        />
      ) : (
        <Globe className="size-4 shrink-0 text-muted-foreground" />
      )}
      {name}
    </span>
  )
}
