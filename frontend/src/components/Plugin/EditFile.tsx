// TODO: Validate
import { zodResolver } from "@hookform/resolvers/zod"
import { useMutation, useQuery } from "@tanstack/react-query"
import { useParams } from "@tanstack/react-router"
import { ChevronDown, ChevronRight, Pencil } from "lucide-react"
import { useEffect, useState } from "react"
import { useForm } from "react-hook-form"
import { z } from "zod"

import { FilesService, type FileUpdate } from "@/client"
import { FormModal } from "@/components/Common/FormModal"
import { FormTextArea } from "@/components/Common/FormTextArea"
import { FormTextField } from "@/components/Common/FormTextField"
import { TooltipIconButton } from "@/components/Common/TooltipIconButton"
import { Button } from "@/components/ui/button"
import useCustomToast from "@/hooks/useCustomToast"
import { optionalString, requiredKey } from "@/lib/formSchemas"
import { handleError } from "@/utils"

import type { FileTableData } from "./fileColumns"

type FilesData = Array<FileTableData>

const formSchema = z.object({
  key: requiredKey,
  data_timestamp: z.string().min(1, "Data timestamp is required"),
  content: optionalString,
  update_at: optionalString,
  extra: optionalString,
})

type FormInput = z.input<typeof formSchema>
type FormOutput = z.output<typeof formSchema>

interface EditFileProps {
  file: FileTableData
}

const EditFile = ({ file }: EditFileProps) => {
  const { pluginId } = useParams({ strict: false })
  const [isOpen, setIsOpen] = useState(false)
  const [showContent, setShowContent] = useState(false)
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const queryKey = ["plugins", pluginId, "files"]

  const form = useForm<FormInput, unknown, FormOutput>({
    resolver: zodResolver(formSchema),
    mode: "onBlur",
    criteriaMode: "all",
    defaultValues: {
      key: file.key ?? "",
      data_timestamp: file.data_timestamp?.slice(0, 16) ?? "",
      content: "",
      update_at: file.update_at?.slice(0, 16) ?? "",
      extra: file.extra ?? "",
    },
  })

  // content is excluded from the files list response, so fetch the full file
  // when the modal opens to populate the content field.
  const { data: fullFile } = useQuery({
    queryKey: ["files", file.id],
    queryFn: () => FilesService.getFile({ fileId: file.id }),
    enabled: isOpen,
  })

  useEffect(() => {
    if (fullFile) {
      form.setValue("content", fullFile.content ?? "")
    }
  }, [fullFile, form])

  const mutation = useMutation({
    mutationFn: (data: FileUpdate) =>
      FilesService.updateFile({ fileId: file.id, requestBody: data }),
    // When mutate is called:
    onMutate: async (newData, context) => {
      // Cancel any outgoing refetches
      // (so they don't overwrite our optimistic update)
      await context.client.cancelQueries({ queryKey })
      // Snapshot the previous value
      const previous = context.client.getQueriesData<FilesData>({ queryKey })

      // Optimistically update to the new value
      context.client.setQueriesData<FilesData>({ queryKey }, (old) =>
        old?.map((existing) =>
          existing.id === file.id
            ? ({ ...existing, ...newData, pending: true } as FileTableData)
            : existing,
        ),
      )

      // Return a result with the snapshotted value
      return { previous }
    },
    onSuccess: () => {
      showSuccessToast("File updated successfully")
    },
    // If the mutation fails,
    // use the result returned from onMutate to roll back
    onError: (error, _newData, onMutateResult, context) => {
      for (const [key, data] of onMutateResult?.previous ?? []) {
        context.client.setQueryData(key, data)
      }
      handleError.call(showErrorToast, error as any)
    },
    // Always refetch after error or success:
    onSettled: (_data, _error, _variables, _onMutateResult, context) => {
      context.client.invalidateQueries({ queryKey })
      context.client.invalidateQueries({ queryKey: ["files", file.id] })
    },
  })

  const onSubmit = (data: FormOutput) => {
    setIsOpen(false)
    mutation.mutate(data)
  }

  return (
    <FormModal
      open={isOpen}
      onOpenChange={setIsOpen}
      trigger={
        <TooltipIconButton
          label="Edit File"
          icon={<Pencil />}
          onClick={() => setIsOpen(true)}
        />
      }
      title="Edit File"
      description="Update the file details below."
      form={form}
      onSubmit={onSubmit}
      isPending={mutation.isPending}
    >
      <FormTextField control={form.control} label="Key" type="text" />
      <FormTextField
        control={form.control}
        label="Data Timestamp"
        type="datetime-local"
        required
      />
      <FormTextField
        control={form.control}
        label="Update At"
        type="datetime-local"
        showNowButton
      />
      <Button
        type="button"
        variant="ghost"
        size="sm"
        className="w-fit px-2"
        onClick={() => setShowContent((previous) => !previous)}
      >
        {showContent ? <ChevronDown /> : <ChevronRight />}
        Content
      </Button>
      {showContent && (
        <FormTextArea
          control={form.control}
          label="Content"
          placeholder="File content..."
          rows={8}
        />
      )}
      <FormTextField control={form.control} label="Extra" type="text" />
    </FormModal>
  )
}

export default EditFile
