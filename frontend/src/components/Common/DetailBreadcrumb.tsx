// TODO: Validate
import { Link } from "@tanstack/react-router"
import { Fragment, type ReactNode } from "react"

import type {
  PluginOutput,
  SeasonOutput,
  ShowPublic,
  SourcePublic,
} from "@/client"
import EditPlugin from "@/components/Plugins/Edit"
import EditSeason from "@/components/Seasons/Edit"
import EditShow from "@/components/Shows/Edit"
import EditSource from "@/components/Sources/Edit"
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb"

export type EntityKey = "plugin" | "source" | "show" | "season"

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
  const crumbs: {
    key: EntityKey
    label: string
    link: ReactNode
    edit: ReactNode
  }[] = []
  if (plugin) {
    crumbs.push({
      key: "plugin",
      label: plugin.name || plugin.key,
      link: (
        <Link to="/sources" search={{ plugin_id: plugin.id }}>
          {plugin.name || plugin.key}
        </Link>
      ),
      edit: <EditPlugin plugin={plugin} size="icon-sm" />,
    })
  }
  if (source) {
    crumbs.push({
      key: "source",
      label: source.name || source.key,
      link: (
        <Link to="/shows" search={{ source_id: source.id }}>
          {source.name || source.key}
        </Link>
      ),
      edit: <EditSource source={source} size="icon-sm" />,
    })
  }
  if (show) {
    crumbs.push({
      key: "show",
      label: show.name || show.key,
      link: (
        <Link to="/seasons" search={{ show_id: show.id }}>
          {show.name || show.key}
        </Link>
      ),
      edit: (
        <EditShow
          show={{ ...show, plugin_name: plugin?.name ?? null }}
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
      edit: <EditSeason season={season} size="icon-sm" />,
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
