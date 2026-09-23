import http from './http'
import { patchQuote } from './quote'

export interface BreakdownBody {
  store_name: string
  amount: number | null
  note: string | null
}

export async function addBreakdown(quoteId: number | string, body: BreakdownBody) {
  return await http.post<never, any>(`/quotes/${quoteId}/breakdowns`, body)
}

export async function patchBreakdown(quoteId: number | string, id: number, body: BreakdownBody) {
  return await http.patch<never, any>(`/quotes/${quoteId}/breakdowns/${id}`, body)
}

export async function deleteBreakdown(quoteId: number | string, id: number) {
  return await http.delete<never, any>(`/quotes/${quoteId}/breakdowns/${id}`)
}

export { patchQuote }
