import { apiFetch } from './client'

export const notificationsApi = {
  list({ unreadOnly = false, page = 0, size = 20, signal } = {}) {
    const params = new URLSearchParams({
      unreadOnly: String(unreadOnly),
      page: String(page),
      size: String(size),
    })

    return apiFetch(`/notifications?${params}`, { signal })
  },

  read(notificationId) {
    return apiFetch(
      `/notifications/${encodeURIComponent(notificationId)}/read`,
      { method: 'PATCH' },
    )
  },

  readAll() {
    return apiFetch('/notifications/read-all', {
      method: 'PATCH',
    })
  },
}

// 현재 탭에서 읽음 처리가 발생하면 헤더의 개수를 다시 조회한다.
// 알림을 실시간 수신하는 WebSocket 기능은 포함하지 않는다.
export function notifyNotificationsChanged() {
  window.dispatchEvent(new Event('notifications-updated'))
}
