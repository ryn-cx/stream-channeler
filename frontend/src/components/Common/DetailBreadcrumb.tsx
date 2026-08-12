// TODO: Validate
import { Link } from "@tanstack/react-router"
import { Fragment, type ReactNode } from "react"

import type {
  CanonicalSeasonOutput,
  CanonicalShowOutput,
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

type EntityKey =
  | "plugin"
  | "source"
  | "show"
  | "season"
  | "canonicalShow"
  | "canonicalSeason"

interface DetailBreadcrumbProps {
  plugin?: PluginOutput
  source?: SourcePublic
  show?: ShowPublic
  season?: SeasonOutput
  canonicalShow?: CanonicalShowOutput
  canonicalSeason?: CanonicalSeasonOutput
  trailing: string
  current?: EntityKey
}

// TODO: Validate
export function DetailBreadcrumb({
  plugin,
  source,
  show,
  season,
  canonicalShow,
  canonicalSeason,
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
  // A canonical row's key is unset until something claims it, so the id is the
  // last thing left to name it by.
  if (canonicalShow) {
    const label = canonicalShow.name || canonicalShow.key || canonicalShow.id
    crumbs.push({
      key: "canonicalShow",
      label,
      link: (
        <Link
          to="/admin/canonical-show/$canonicalShowId"
          params={{ canonicalShowId: canonicalShow.id }}
        >
          {label}
        </Link>
      ),
    })
  }
  if (canonicalSeason) {
    const label =
      canonicalSeason.name || canonicalSeason.key || canonicalSeason.id
    crumbs.push({
      key: "canonicalSeason",
      label,
      link: (
        <Link
          to="/admin/canonical-season/$canonicalSeasonId"
          params={{ canonicalSeasonId: canonicalSeason.id }}
        >
          {label}
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
