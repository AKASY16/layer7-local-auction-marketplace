import { apiFetch } from './client'

export const auctionCreateApi = {
  getBidIncrementPolicy(signal) {
    return apiFetch('/bid-increment-policy', { signal })
  },

  create(productId, data, signal) {
    return apiFetch(`/products/${encodeURIComponent(productId)}/auctions`, {
      method: 'POST',
      body: data,
      signal,
    })
  },
}
