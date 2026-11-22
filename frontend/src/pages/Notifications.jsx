import { useEffect, useRef, useState, useSyncExternalStore } from 'react'
import { Link, useNavigate } from 'react-router'
import styled from 'styled-components'

import { getAuthUser, subscribeAuth } from '../api/client'
import {
  notificationsApi,
  notifyNotificationsChanged,
} from '../api/notifications'
import Button from '../components/common/Button'

const PAGE_SIZE = 20

const Page = styled.section`
  display: grid;
  gap: ${({ theme }) => theme.space.lg};
  padding: ${({ theme }) => theme.space.xl} 0 40px;
`

const Heading = styled.h2`
  margin: 0;
  color: ${({ theme }) => theme.colors.primaryDark};
  font-size: ${({ theme }) => theme.fontSizes.title};
`

const Row = styled.div`
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: ${({ theme }) => theme.space.sm};
  flex-wrap: wrap;
`

const List = styled.ul`
  display: grid;
  gap: ${({ theme }) => theme.space.sm};
  padding: 0;
  margin: 0;
  list-style: none;
`

const ItemButton = styled.button`
  display: grid;
  width: 100%;
  gap: ${({ theme }) => theme.space.sm};
  padding: ${({ theme }) => theme.space.lg};
  border: 1px solid
    ${({ theme, $unread }) =>
      $unread ? theme.colors.primary : theme.colors.border};
  border-radius: ${({ theme }) => theme.radius.box};
  background: ${({ theme, $unread }) =>
    $unread ? theme.colors.primaryTint : theme.colors.background};
  color: ${({ theme }) => theme.colors.text};
  font: inherit;
  text-align: left;
  cursor: pointer;

  &:disabled {
    cursor: wait;
    opacity: 0.7;
  }

  &:focus-visible {
    outline: 2px solid ${({ theme }) => theme.colors.primary};
    outline-offset: 2px;
  }
`

const Message = styled.p`
  margin: 0;
  overflow-wrap: anywhere;
  line-height: 1.5;
`

const Meta = styled.span`
  font-size: ${({ theme }) => theme.fontSizes.sub};
  color: ${({ theme }) => theme.colors.textSub};
`

const Status = styled.span`
  color: ${({ theme, $unread }) =>
    $unread ? theme.colors.primary : theme.colors.textSub};
  font-size: ${({ theme }) => theme.fontSizes.sub};
  font-weight: ${({ theme, $unread }) =>
    $unread ? theme.fontWeights.semibold : theme.fontWeights.regular};
`

const ErrorText = styled.p`
  color: ${({ theme }) => theme.colors.danger};
`

function formatDate(value) {
  const timestamp = Date.parse(value)

  if (!Number.isFinite(timestamp)) {
    return '시간 정보 없음'
  }

  return new Date(timestamp).toLocaleString('ko-KR')
}

function Notifications() {
  const navigate = useNavigate()
  const user = useSyncExternalStore(subscribeAuth, getAuthUser, getAuthUser)

  const userId = user?.id ?? null
  const signedIn = userId != null

  const [pagination, setPagination] = useState({
    ownerId: null,
    page: 0,
  })

  const page = pagination.ownerId === userId ? pagination.page : 0

  const [revision, setRevision] = useState(0)

  const [result, setResult] = useState(null)
  const [actionError, setActionError] = useState('')
  const [pendingId, setPendingId] = useState(null)
  const [readingAll, setReadingAll] = useState(false)

  const requestBusy = useRef(false)

  const resultKey = `${userId}:${page}:${revision}`

  // 사용자와 페이지가 일치하는 응답만 화면에 표시한다.
  const currentResult = result?.key === resultKey ? result : null

  const data = currentResult?.data ?? null
  const loading = signedIn && currentResult == null
  const error = currentResult?.error ?? ''

  useEffect(() => {
    if (userId == null) {
      return undefined
    }

    const controller = new AbortController()

    notificationsApi
      .list({
        unreadOnly: false,
        page,
        size: PAGE_SIZE,
        signal: controller.signal,
      })
      .then((response) => {
        if (controller.signal.aborted) return

        setResult({
          key: resultKey,
          data: response,
          error: '',
        })
      })
      .catch((requestError) => {
        if (controller.signal.aborted) return

        setResult({
          key: resultKey,
          data: null,
          error: requestError.message || '알림 목록을 불러오지 못했습니다.',
        })
      })

    return () => controller.abort()
  }, [userId, page, revision, resultKey])

  function refresh() {
    setRevision((value) => value + 1)
  }

  function goToPage(nextPage) {
    if (requestBusy.current) return

    setPagination({
      ownerId: userId,
      page: nextPage,
    })
  }

  async function handleRead(notification) {
    if (requestBusy.current) return

    requestBusy.current = true
    setPendingId(notification.id)
    setActionError('')

    try {
      if (notification.readAt == null) {
        const updated = await notificationsApi.read(notification.id)

        setResult((previous) => {
          if (previous?.key !== resultKey || !previous.data) {
            return previous
          }

          return {
            ...previous,
            data: {
              ...previous.data,
              content: previous.data.content.map((item) =>
                item.id === notification.id ? updated : item,
              ),
            },
          }
        })

        notifyNotificationsChanged()
      }

      if (notification.auctionId != null) {
        navigate(`/auctions/${notification.auctionId}`)
      }
    } catch (requestError) {
      setActionError(requestError.message || '알림 읽음 처리에 실패했습니다.')
    } finally {
      requestBusy.current = false
      setPendingId(null)
    }
  }

  async function handleReadAll() {
    if (requestBusy.current) return

    requestBusy.current = true
    setReadingAll(true)
    setActionError('')

    try {
      await notificationsApi.readAll()

      notifyNotificationsChanged()
      refresh()
    } catch (requestError) {
      setActionError(requestError.message || '모두 읽음 처리에 실패했습니다.')
    } finally {
      requestBusy.current = false
      setReadingAll(false)
    }
  }

  if (!signedIn) {
    return (
      <Page>
        <Heading>알림</Heading>
        <p>알림을 확인하려면 로그인해야 합니다.</p>
        <Link to="/login">로그인하러 가기</Link>
      </Page>
    )
  }

  const notifications = Array.isArray(data?.content) ? data.content : []

  const totalPages = data?.totalPages ?? 0
  const totalElements = data?.totalElements ?? 0

  return (
    <Page>
      <Row>
        <Heading>알림</Heading>

        <Button
          type="button"
          $size="small"
          $variant="secondary"
          onClick={handleReadAll}
          disabled={loading || readingAll || pendingId != null}
        >
          {readingAll ? '처리 중...' : '모두 읽음'}
        </Button>
      </Row>

      <Row>
        <Meta>전체 {totalElements}개</Meta>

        <Button
          type="button"
          $size="small"
          $variant="secondary"
          onClick={refresh}
          disabled={loading || pendingId != null || readingAll}
        >
          새로고침
        </Button>
      </Row>

      {actionError && <ErrorText role="alert">{actionError}</ErrorText>}

      {loading && <p>알림을 불러오는 중입니다.</p>}

      {error && <ErrorText role="alert">{error}</ErrorText>}

      {!loading && !error && notifications.length === 0 && (
        <p>표시할 알림이 없습니다.</p>
      )}

      {!loading && !error && notifications.length > 0 && (
        <List>
          {notifications.map((notification) => {
            const unread = notification.readAt == null
            const hasAuction = notification.auctionId != null

            return (
              <li key={notification.id}>
                <ItemButton
                  type="button"
                  $unread={unread}
                  disabled={pendingId != null || readingAll}
                  onClick={() => handleRead(notification)}
                  aria-label={`${unread ? '읽지 않은 알림' : '읽은 알림'}: ${notification.message}`}
                >
                  <Row>
                    <Status $unread={unread}>
                      {unread ? '읽지 않음' : '읽음'}
                    </Status>

                    <Meta>{formatDate(notification.createdAt)}</Meta>
                  </Row>

                  <Message>{notification.message}</Message>

                  {hasAuction && <Meta>경매 상세로 이동</Meta>}

                  {!hasAuction && unread && <Meta>누르면 읽음 처리</Meta>}
                </ItemButton>
              </li>
            )
          })}
        </List>
      )}

      {!loading && !error && totalPages > 0 && (
        <Row>
          <Button
            type="button"
            $variant="secondary"
            $size="small"
            disabled={page === 0 || pendingId != null || readingAll}
            onClick={() => goToPage(page - 1)}
          >
            이전
          </Button>

          <Meta>
            {page + 1} / {totalPages}페이지
          </Meta>

          <Button
            type="button"
            $variant="secondary"
            $size="small"
            disabled={page + 1 >= totalPages || pendingId != null || readingAll}
            onClick={() => goToPage(page + 1)}
          >
            다음
          </Button>
        </Row>
      )}
    </Page>
  )
}

export default Notifications
