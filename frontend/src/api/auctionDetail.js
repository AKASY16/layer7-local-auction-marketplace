import { apiFetch } from './client'

export const auctionDetailApi = {
  get(auctionId, signal) {
    return apiFetch(`/auctions/${encodeURIComponent(auctionId)}`, { signal })
  },

  bid(auctionId, amount) {
    return apiFetch(`/auctions/${encodeURIComponent(auctionId)}/bids`, {
      method: 'POST',
      body: { amount },
    })
  },

  bids(auctionId, page = 0, size = 20, signal) {
    const params = new URLSearchParams({
      page: String(page),
      size: String(size),
    })

    return apiFetch(
      `/auctions/${encodeURIComponent(auctionId)}/bids?${params}`,
      { signal },
    )
  },

  pricePolicy(signal) {
    return apiFetch('/bid-increment-policy', { signal })
  },
}
