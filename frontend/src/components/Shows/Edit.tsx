// TODO: Validate
import { zodResolver } from "@hookform/resolvers/zod"
import { Pencil } from "lucide-react"
import { useState } from "react"
import { useForm } from "react-hook-form"
import { z } from "zod"

import { ShowsService, type ShowUpdate } from "@/client"
import { AdminZone } from "@/components/Common/AdminZone"
import { FormModal } from "@/components/Common/FormModal"
import { FormTextField } from "@/components/Common/FormTextField"
import { TooltipIconButton } from "@/components/Common/TooltipIconButton"
import { useEditTableRow } from "@/components/Common/useEditTableRow"
import useAuth from "@/hooks/useAuth"
import { nullifyBlanks, optionalString, requiredKey } from "@/lib/formSchemas"

import type { ShowTableData } from "./columns"
import {
  episodeGroupIdOf,
  extraForEpisodeGroupId,
  TMDB_EPISODE_ORDER_PLUGIN,
  TmdbEpisodeOrderField,
} from "./TmdbEpisodeOrderField"

const formSchema = z.object({
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
  show: ShowTableData
}

// TODO: Validate
const EditShow = ({ show }: EditShowProps) => {
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
  })

  // TODO: Validate
  const onSubmit = (data: FormOutput) => {
    setIsOpen(false)
    // `extra` is only sent where the order is being edited, since another
    // plugin keeps its own things there and a blank would write them away.
    const update = nullifyBlanks(data)
    mutation.mutate(
      showsEpisodeOrder
        ? { ...update, extra: extraForEpisodeGroupId(episodeGroupId) }
        : update,
    )
  }

  return (
    <FormModal
      open={isOpen}
      onOpenChange={setIsOpen}
      trigger={
        <TooltipIconButton
          label="Edit Show"
          icon={<Pencil />}
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
        label="TMDB ID"
        placeholder="12345"
        type="number"
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
