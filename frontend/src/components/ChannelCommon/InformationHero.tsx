// TODO: Validate
import { ExternalLink } from "lucide-react"
import type { ReactNode } from "react"

import { ClampedContent } from "@/components/ChannelCommon/ClampedContent"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"

interface InformationHeroLink {
  label: string
  href: string
}

interface InformationHeroProps {
  title: string
  subtitle?: string | null
  description?: string | null
  imageUrl?: string | null
  /** Short facts shown as chips under the title, e.g. duration or air date. */
  facts?: string[]
  links?: InformationHeroLink[]
  titleAction?: ReactNode
}

// TODO: Validate
/**
 * The record as it reads at a glance, ahead of the field-by-field comparison.
 *
 * The artwork and the few facts worth reading first are laid out on their own so
 * the table below is there to be checked rather than to be read.
 */
// TODO: Validate
export function InformationHero({
  title,
  subtitle,
  description,
  imageUrl,
  facts = [],
  links = [],
  titleAction,
}: InformationHeroProps) {
  return (
    <div className="overflow-hidden rounded-xl border bg-linear-to-br from-muted/60 to-background">
      <div className="flex flex-col gap-4 p-4 sm:flex-row sm:gap-6">
        {imageUrl && (
          <img
            referrerPolicy="no-referrer"
            src={imageUrl}
            alt={title}
            className="max-h-64 w-full shrink-0 self-start rounded-lg object-cover sm:w-48"
          />
        )}
        <div className="flex min-w-0 flex-col gap-2">
          <div>
            <div className="flex items-start gap-2">
              <h2 className="text-xl font-semibold wrap-break-word">{title}</h2>
              {titleAction}
            </div>
            {subtitle && (
              <p className="text-sm text-muted-foreground wrap-break-word">
                {subtitle}
              </p>
            )}
          </div>

          {facts.length > 0 && (
            <div className="flex flex-wrap gap-1">
              {facts.map((fact) => (
                <Badge key={fact} variant="secondary">
                  {fact}
                </Badge>
              ))}
            </div>
          )}

          {description && (
            <ClampedContent className="whitespace-pre-wrap text-sm text-muted-foreground">
              {description}
            </ClampedContent>
          )}

          {links.length > 0 && (
            <div className="mt-auto flex flex-wrap gap-2 pt-1">
              {links.map((link) => (
                <Button key={link.href} variant="outline" size="sm" asChild>
                  <a href={link.href} target="_blank" rel="noopener noreferrer">
                    {link.label}
                    <ExternalLink className="ml-1 h-3 w-3" />
                  </a>
                </Button>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
