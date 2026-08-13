// TODO: Validate
import { Link } from "@tanstack/react-router"
import { Fragment, type ReactNode } from "react"

import type {
  PluginOutput,
  SeasonOutput,
  ShowPublic,
  SourcePublic,
} from "@/client"
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb"

type EntityKey = "plugin" | "source" | "show" | "season"

interface DetailBreadcrumbProps {
  plugin?: PluginOutput
  source?: SourcePublic
  show?: ShowPublic
  season?: SeasonOutput
  trailing: string
  current?: EntityKey
}

// TODO: Validate
export function DetailBreadcrumb({
  plugin,
  source,
  show,
  season,
  trailing,
  current,
}: DetailBreadcrumbProps) {
  const crumbs: { key: EntityKey; label: string; link: ReactNode }[] = []
  if (plugin) {
    crumbs.push({
      key: "plugin",
      label: plugin.name || plugin.key,
      link: (
        <Link to="/plugin/$pluginId" params={{ pluginId: plugin.id }}>
          {plugin.name || plugin.key}
        </Link>
      ),
    })
  }
  if (source) {
    crumbs.push({
      key: "source",
      label: source.name || source.key,
      link: (
        <Link to="/source/$sourceKey" params={{ sourceKey: source.id }}>
          {source.name || source.key}
        </Link>
      ),
    })
  }
  if (show) {
    crumbs.push({
      key: "show",
      label: show.name || show.key,
      link: (
        <Link to="/show/$showKey" params={{ showKey: show.id }}>
          {show.name || show.key}
        </Link>
      ),
    })
  }
  if (season) {
    crumbs.push({
      key: "season",
      label: season.name || season.key,
      link: (
        <Link to="/season/$seasonKey" params={{ seasonKey: season.id }}>
          {season.name || season.key}
        </Link>
      ),
    })
  }
  return (
    <Breadcrumb>
      <BreadcrumbList className="text-foreground gap-1.5 text-2xl font-bold tracking-tight sm:gap-1.5">
        {crumbs.map((crumb) => (
          <Fragment key={crumb.key}>
            <BreadcrumbItem>
              {crumb.key === current ? (
                <span>{crumb.label}</span>
              ) : (
                <BreadcrumbLink
                  asChild
                  className="text-primary hover:text-primary hover:underline"
                >
                  {crumb.link}
                </BreadcrumbLink>
              )}
            </BreadcrumbItem>
            <BreadcrumbSeparator className="text-muted-foreground" />
          </Fragment>
        ))}
        <BreadcrumbItem>
          <BreadcrumbPage className="text-foreground font-bold">
            {trailing}
          </BreadcrumbPage>
        </BreadcrumbItem>
      </BreadcrumbList>
    </Breadcrumb>
  )
}
