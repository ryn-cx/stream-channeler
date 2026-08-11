// TODO: Validate
import { useMutation } from "@tanstack/react-query"

import type { MediaTableResult } from "@/components/Common/DataTable"
import { queryHasRow } from "@/components/Common/useDeleteTableRow"
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"

type TableRow = { id: string; pending?: boolean }
type TableResult = MediaTableResult<TableRow>

interface UseEditTableRowOptions<TVariables> {
  mutationFn: (data: TVariables) => Promise<unknown>
  rowId: string
  successMessage: string
  extraInvalidateKeys?: readonly unknown[][]
}

// TODO: Validate
export function useEditTableRow<TVariables extends object>({
  mutationFn,
  rowId,
  successMessage,
  extraInvalidateKeys = [],
}: UseEditTableRowOptions<TVariables>) {
  const { showSuccessToast, showErrorToast } = useCustomToast()

  return useMutation({
    mutationFn,
    // When mutate is called:
    onMutate: async (newData, context) => {
      // Match every cached table holding this row, regardless of which page's
      // query key it belongs to (rows appear on both the top-level list and
      // the scoped detail pages, which use different keys).
      const filters = { predicate: queryHasRow(rowId) }
      // Cancel any outgoing refetches
      // (so they don't overwrite our optimistic update)
      await context.client.cancelQueries(filters)
      // Snapshot the previous value
      const previous = context.client.getQueriesData<TableResult>(filters)

      // Optimistically update to the new value
      context.client.setQueriesData<TableResult>(filters, (old) =>
        old
          ? {
              ...old,
              data: old.data.map((row) =>
                row.id === rowId ? { ...row, ...newData, pending: true } : row,
              ),
            }
          : old,
      )

      // Return a result with the snapshotted value
      return { previous }
    },
    onSuccess: () => {
      showSuccessToast(successMessage)
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
    onSettled: (_data, _error, _variables, onMutateResult, context) => {
      for (const [key] of onMutateResult?.previous ?? []) {
        context.client.invalidateQueries({ queryKey: key })
      }
      for (const key of extraInvalidateKeys) {
        context.client.invalidateQueries({ queryKey: key })
      }
    },
  })
}
