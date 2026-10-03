// TODO: Validate
import { type Query, useMutation } from "@tanstack/react-query"

import type { MediaTableResult } from "@/components/Common/DataTable"
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"

type TableRow = { id: string; pending?: boolean }
type TableResult = MediaTableResult<TableRow>

// TODO: Validate
const isTableResult = (data: unknown): data is TableResult =>
  typeof data === "object" &&
  data !== null &&
  Array.isArray((data as TableResult).data)

// TODO: Validate
export const queryHasRow =
  (rowId: string) =>
  (query: Query): boolean =>
    isTableResult(query.state.data) &&
    query.state.data.data.some((row) => row.id === rowId)

interface UseDeleteTableRowOptions {
  mutationFn: (id: string) => Promise<unknown>
  rowId: string
  successMessage: string
}

// TODO: Validate
export function useDeleteTableRow({
  mutationFn,
  rowId,
  successMessage,
}: UseDeleteTableRowOptions) {
  const { showSuccessToast, showErrorToast } = useCustomToast()

  return useMutation({
    mutationFn,
    // When mutate is called:
    onMutate: async (_id, context) => {
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
                row.id === rowId ? { ...row, pending: true } : row,
              ),
            }
          : old,
      )

      // Return a result with the snapshotted value
      return { previous }
    },
    onSuccess: (_data, _variables, _onMutateResult, context) => {
      showSuccessToast(successMessage)
      context.client.setQueriesData<TableResult>(
        { predicate: queryHasRow(rowId) },
        (old) =>
          old
            ? { ...old, data: old.data.filter((row) => row.id !== rowId) }
            : old,
      )
    },
    // If the mutation fails,
    // use the result returned from onMutate to roll back
    onError: (error, _variables, onMutateResult, context) => {
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
    },
  })
}
