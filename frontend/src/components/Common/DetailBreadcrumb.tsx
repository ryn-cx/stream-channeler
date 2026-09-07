// TODO: Validate
import { Link } from "@tanstack/react-router"
import { Fragment, type ReactNode } from "react"

import type {
  PluginOutput,
  SeasonOutput,
  SourcePublic,
  TitlePublic,
} from "@/client"
import EditTitle from "@/components/Titles/Edit"
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb"

export type EntityKey = "plugin" | "source" | "title" | "season"

interface DetailBreadcrumbProps {
  plugin?: PluginOutput
  source?: SourcePublic
  title?: TitlePublic
  season?: SeasonOutput
  trailing: string
  current?: EntityKey
}

// TODO: Validate
export function DetailBreadcrumb({
  plugin,
  source,
  title,
  season,
  trailing,
  current,
}: DetailBreadcrumbProps) {
  const crumbs: {
    key: EntityKey
    label: string
    link: ReactNode
    edit?: ReactNode
  }[] = []
  if (plugin) {
    crumbs.push({
      key: "plugin",
      label: plugin.key,
      link: (
        <Link to="/sources" search={{ plugin_id: plugin.id }}>
          {plugin.key}
        </Link>
      ),
    })
  }
  if (source) {
    crumbs.push({
      key: "source",
      label: source.key,
      link: (
        <Link to="/titles" search={{ source_id: source.id }}>
          {source.key}
        </Link>
      ),
    })
  }
  if (title) {
    crumbs.push({
      key: "title",
      label: title.name || title.key,
      link: (
        <Link to="/seasons" search={{ title_id: title.id }}>
          {title.name || title.key}
        </Link>
      ),
      edit: (
        <EditTitle
          title={{ ...title, plugin_name: plugin?.key ?? null }}
          size="icon-sm"
        />
      ),
    })
  }
  if (season) {
    crumbs.push({
      key: "season",
      label: season.name || season.key,
      link: (
        <Link to="/episodes" search={{ season_id: season.id }}>
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
              {crumb.edit}
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
