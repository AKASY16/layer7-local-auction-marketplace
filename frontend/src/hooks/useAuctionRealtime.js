import { useEffect, useRef, useState } from 'react'
import { Client } from '@stomp/stompjs'
import { getAccessToken } from '../api/client'

function useAuctionRealtime(auctionId, onEvent, onConnected, authIdentity) {
  const [connectionStatus, setConnectionStatus] = useState('connecting')

  const callbacksRef = useRef({
    onEvent,
    onConnected,
  })

  useEffect(() => {
    callbacksRef.current = {
      onEvent,
      onConnected,
    }
  }, [onEvent, onConnected])

  useEffect(() => {
    if (!/^[1-9]\d*$/.test(String(auctionId ?? ''))) {
      return undefined
    }

    let disposed = false
    let connectedOnce = false

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const brokerURL = `${protocol}//${window.location.host}/ws`

    const client = new Client({
      brokerURL,
      reconnectDelay: 3000,
      heartbeatIncoming: 10000,
      heartbeatOutgoing: 10000,

      connectHeaders: getAccessToken()
        ? {
            Authorization: `Bearer ${getAccessToken()}`,
          }
        : {},

      onConnect: () => {
        if (disposed) return

        const reconnected = connectedOnce
        connectedOnce = true

        client.subscribe(`/topic/auctions/${auctionId}`, (message) => {
          if (disposed) return

          try {
            const event = JSON.parse(message.body)

            if (!event || String(event.auctionId) !== String(auctionId)) {
              return
            }

            callbacksRef.current.onEvent(event)
          } catch {
            // 잘못된 메시지는 화면 상태에 반영하지 않는다.
          }
        })

        setConnectionStatus('connected')

        // 최초 구독과 재연결 모두 REST를 다시 조회한다.
        // 구독이 완료된 뒤 조회해 이벤트 유실 구간을 줄인다.
        callbacksRef.current.onConnected(reconnected)
      },

      onWebSocketClose: () => {
        if (!disposed) {
          setConnectionStatus('disconnected')
        }
      },

      onWebSocketError: () => {
        if (!disposed) {
          setConnectionStatus('disconnected')
        }
      },

      onStompError: () => {
        if (!disposed) {
          setConnectionStatus('disconnected')
        }
      },
    })

    client.activate()

    return () => {
      disposed = true
      void client.deactivate()
    }
  }, [auctionId, authIdentity])

  return connectionStatus
}

export default useAuctionRealtime
