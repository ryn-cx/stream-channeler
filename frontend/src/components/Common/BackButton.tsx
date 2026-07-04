// TODO: Validate
import { Link, type LinkProps } from "@tanstack/react-router"
import { ArrowLeft } from "lucide-react"

import { Button } from "@/components/ui/button"

export function BackButton(props: LinkProps) {
  return (
    <Button variant="ghost" size="icon" asChild>
      <Link {...props}>
        <ArrowLeft />
      </Link>
    </Button>
  )
}
