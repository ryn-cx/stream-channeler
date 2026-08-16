// TODO: Validate
import { zodResolver } from "@hookform/resolvers/zod"
import { Pencil } from "lucide-react"
import { useState } from "react"
import { useForm } from "react-hook-form"
import { z } from "zod"

import { type ShowPublic, ShowsService, type ShowUpdate } from "@/client"
import { AdminZone } from "@/components/Common/AdminZone"
import { FormCheckboxField } from "@/components/Common/FormCheckboxField"
import { FormModal } from "@/components/Common/FormModal"
import { FormTextField } from "@/components/Common/FormTextField"
import { TooltipIconButton } from "@/components/Common/TooltipIconButton"
import { useEditTableRow } from "@/components/Common/useEditTableRow"
import useAuth from "@/hooks/useAuth"
import { extraText, parseExtraText } from "@/lib/extra"
import {
  nullifyBlanks,
  optionalInt,
  optionalString,
  requiredKey,
} from "@/lib/formSchemas"

import { CanonicalShowField } from "./CanonicalShowField"
import {
  episodeGroupIdOf,
  TMDB_EPISODE_ORDER_PLUGIN,
  TmdbEpisodeOrderField,
  withEpisodeGroupId,
} from "./TmdbEpisodeOrderField"

const formSchema = z.object({
  year: optionalInt,
  canonical_show_locked: z.boolean(),
  canonical_show_note: optionalString,
  deleted_at: optionalString,
  extra: optionalString,
  key: requiredKey,
  name: optionalString,
  media_type: optionalString,
  description: optionalString,
  url: optionalString,
  image_url: optionalString,
  data_timestamp: optionalString,
  update_at: optionalString,
})

type FormInput = z.input<typeof formSchema>
type FormOutput = z.output<typeof formSchema>

interface EditShowProps {
  show: ShowPublic & { plugin_name?: string | null }
  size?: React.ComponentProps<typeof TooltipIconButton>["size"]
}

// TODO: Validate
const EditShow = ({ show, size }: EditShowProps) => {
  const [isOpen, setIsOpen] = useState(false)
  const { user } = useAuth()
  // Only TMDB's own rows carry an episode order, and only an admin sets one.
  const showsEpisodeOrder =
    Boolean(user?.is_superuser) &&
    show.plugin_name === TMDB_EPISODE_ORDER_PLUGIN
  const [episodeGroupId, setEpisodeGroupId] = useState(() =>
    episodeGroupIdOf(show.extra),
  )

  const form = useForm<FormInput, unknown, FormOutput>({
    resolver: zodResolver(formSchema),
    mode: "onBlur",
    criteriaMode: "all",
    defaultValues: {
      year: show.year == null ? "" : String(show.year),
      canonical_show_locked: show.canonical_show_locked ?? false,
      canonical_show_note: show.canonical_show_note ?? "",
      deleted_at: show.deleted_at?.slice(0, 16) ?? "",
      extra: extraText(show.extra),
      key: show.key ?? "",
      name: show.name ?? "",
      media_type: show.media_type ?? "",
      description: show.description ?? "",
      url: show.url ?? "",
      image_url: show.image_url ?? "",
      data_timestamp: show.data_timestamp?.slice(0, 16) ?? "",
      update_at: show.update_at?.slice(0, 16) ?? "",
    },
  })

  const mutation = useEditTableRow<ShowUpdate>({
    mutationFn: (data) =>
      ShowsService.updateShow({ showId: show.id, requestBody: data }),
    rowId: show.id,
    successMessage: "Show updated successfully",
    extraInvalidateKeys: [["shows", show.id]],
  })

  // TODO: Validate
  const onSubmit = (data: FormOutput) => {
    setIsOpen(false)
    // The order is written onto whatever else `extra` holds rather than over
    // it, since the box above edits the same column and a plugin keeps its own
    // things there too.
    const extra = parseExtraText(data.extra ?? "")
    mutation.mutate({
      ...nullifyBlanks(data),
      extra: showsEpisodeOrder
        ? withEpisodeGroupId(extra, episodeGroupId)
        : extra,
    })
  }

  return (
    <FormModal
      open={isOpen}
      onOpenChange={setIsOpen}
      trigger={
        <TooltipIconButton
          label="Edit Show"
          icon={<Pencil />}
          size={size}
          onClick={() => setIsOpen(true)}
        />
      }
      title="Edit Show"
      description="Update the show details below."
      form={form}
      onSubmit={onSubmit}
      isPending={mutation.isPending}
    >
      <FormTextField
        control={form.control}
        label="Name"
        placeholder="Show name"
        type="text"
      />
      <FormTextField
        control={form.control}
        label="Media Type"
        placeholder="e.g. anime, series"
        type="text"
      />
      <FormTextField
        control={form.control}
        label="Description"
        placeholder="Description"
        type="text"
      />
      <FormTextField
        control={form.control}
        label="URL"
        placeholder="https://..."
        type="url"
      />
      <FormTextField
        control={form.control}
        label="Image URL"
        placeholder="https://..."
        type="url"
      />
      <FormTextField
        control={form.control}
        label="Data Timestamp"
        type="datetime-local"
      />
      <FormTextField
        control={form.control}
        label="Update At"
        type="datetime-local"
        showNowButton
      />
      <FormTextField control={form.control} label="Key" type="text" />
      <FormTextField control={form.control} label="Year" type="number" />
      <FormTextField
        control={form.control}
        label="Canonical Show Note"
        type="text"
      />
      <FormCheckboxField control={form.control} label="Canonical Show Locked" />
      <FormTextField
        control={form.control}
        label="Deleted At"
        type="datetime-local"
      />
      <FormTextField control={form.control} label="Extra" type="text" />
      {user?.is_superuser && (
        <AdminZone>
          <CanonicalShowField
            showId={show.id}
            canonicalShowId={show.canonical_show_id}
            enabled={isOpen}
          />
        </AdminZone>
      )}
      {showsEpisodeOrder && (
        <AdminZone>
          <TmdbEpisodeOrderField
            showId={show.id}
            value={episodeGroupId}
            onChange={setEpisodeGroupId}
            enabled={isOpen}
          />
        </AdminZone>
      )}
    </FormModal>
  )
}

export default EditShow
