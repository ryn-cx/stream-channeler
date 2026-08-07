// TODO: Validate

/** A record numbered by its season, its place in that season, and in the title. */
export interface Numbered {
  season_number: number | null
  episode_number: number | null
  absolute_number: number | null
}

/** Which parts of a record's numbering the other record agrees with. */
export interface NumberingAgreement {
  seasonAndEpisode: boolean
  absolute: boolean
}

/** "S2E5", or as much of it as the record was numbered with. */
export function seasonAndEpisodeText(record: Numbered): string {
  if (record.season_number === null && record.episode_number === null) return ""
  return `S${record.season_number ?? "?"}E${record.episode_number ?? "?"}`
}

/** Whether two numbers are the same one, a record with none agreeing with nothing. */
function sameNumber(own: number | null, other: number | null): boolean {
  return own !== null && own === other
}

function sameSeasonAndEpisode(own: Numbered, other: Numbered): boolean {
  return (
    own.season_number !== null &&
    own.episode_number !== null &&
    own.season_number === other.season_number &&
    own.episode_number === other.episode_number
  )
}

/**
 * Which of `own`'s numbers the other record puts the episode at too.
 *
 * The two are compared across as well as like for like, since a website that
 * numbers a title straight through calls TMDB's `S2E8` its own episode 57, so
 * its episode number is answered by TMDB's count through the whole title rather
 * than by TMDB's episode number. Either way of agreeing is worth seeing, since
 * a website and TMDB that put an episode in the same place are far likelier to
 * be talking about the same episode than their differing names suggest.
 */
export function numberingAgreement(
  own: Numbered,
  other: Numbered,
): NumberingAgreement {
  return {
    seasonAndEpisode:
      sameSeasonAndEpisode(own, other) ||
      sameNumber(own.episode_number, other.absolute_number),
    absolute:
      sameNumber(own.absolute_number, other.absolute_number) ||
      sameNumber(own.absolute_number, other.episode_number),
  }
}

/** Whether the two records put the episode in the same place by any of its numbers. */
export function isNumberedTheSame(own: Numbered, other: Numbered): boolean {
  const agreement = numberingAgreement(own, other)
  return agreement.seasonAndEpisode || agreement.absolute
}
