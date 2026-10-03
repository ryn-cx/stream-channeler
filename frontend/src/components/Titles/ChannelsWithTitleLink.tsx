// TODO: Validate
import { Link } from "@tanstack/react-router"
import { Tv } from "lucide-react"

import { Button } from "@/components/ui/button"

// TODO: Validate
export function ChannelsWithTitleLink({ titleId }: { titleId: string }) {
  return (
    <Button variant="outline" size="sm" asChild>
      <Link to="/channels" search={{ title: titleId, view: "public" }}>
        <Tv className="mr-1 h-3 w-3" />
        Channels with this title
      </Link>
    </Button>
  )
}
