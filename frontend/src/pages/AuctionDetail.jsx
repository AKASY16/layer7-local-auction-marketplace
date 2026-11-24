import { useEffect, useRef, useState, useSyncExternalStore } from 'react'
import { Link, useParams } from 'react-router'
import styled from 'styled-components'

import { getAccessToken, getAuthUser, subscribeAuth } from '../api/client'
import { auctionDetailApi } from '../api/auctionDetail'
import useAuctionRealtime from '../hooks/useAuctionRealtime'
import Button from '../components/common/Button'
import {
  Field,
  FieldError,
  FieldMessage,
  Input,
  Label,
} from '../components/common/Field'
import {
  formatPrice,
  formatProductCondition,
  formatRemainingTime,
} from '../utils/format'

const Page = styled.section`
  display: grid;
  gap: ${({ theme }) => theme.space.xl};
  padding: ${({ theme }) => theme.space.xl} 0 40px;
`

const Panel = styled.section`
  display: grid;
  gap: ${({ theme }) => theme.space.md};
  padding: ${({ theme }) => theme.space.lg};
  border: 1px solid ${({ theme }) => theme.colors.border};
  border-radius: ${({ theme }) => theme.radius.box};
`

const Gallery = styled.div`
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: ${({ theme }) => theme.space.sm};
`

const Photo = styled.img`
  display: block;
  width: 100%;
  aspect-ratio: 1;
  object-fit: cover;
  border-radius: ${({ theme }) => theme.radius.control};
`

const Title = styled.h2`
  color: ${({ theme }) => theme.colors.primaryDark};
  font-size: ${({ theme }) => theme.fontSizes.title};
`

const Price = styled.strong`
  color: ${({ theme }) => theme.colors.primary};
  font-size: ${({ theme }) => theme.fontSizes.priceDetail};
`

const Time = styled.strong`
  color: ${({ theme }) => theme.colors.danger};
  font-variant-numeric: tabular-nums;
`

const ConnectionText = styled.span`
  color: ${({ theme }) => theme.colors.textSub};
  font-size: ${({ theme }) => theme.fontSizes.sub};
`

const Grid = styled.dl`
  display: grid;
  grid-template-columns: minmax(96px, 1fr) 2fr;
  gap: ${({ theme }) => theme.space.sm};
  margin: 0;

  dt {
    color: ${({ theme }) => theme.colors.textSub};
  }

  dd {
    margin: 0;
    overflow-wrap: anywhere;
  }
`

const Row = styled.div`
  display: flex;
  align-items: center;
  gap: ${({ theme }) => theme.space.md};
  flex-wrap: wrap;
`

const History = styled.ol`
  padding-left: 20px;
  display: grid;
  gap: ${({ theme }) => theme.space.sm};
`

const BID_PAGE_SIZE = 20

const CONNECTION_LABELS = {
  connecting: '실시간 연결 중',
  connected: '실시간 연결됨',
  disconnected: '연결 끊김 · 재연결 시도 중',
}

function dateLabel(value) {
  if (!value) return '정보 없음'

  const date = new Date(value)

  return Number.isNaN(date.getTime())
    ? '정보 없음'
    : date.toLocaleString('ko-KR')
}

function getLogicalStatus(auction, serverNow) {
  if (!auction) return null

  if (auction.status === 'CANCELED') {
    return 'CANCELED'
  }

  if (auction.status === 'ENDED' || serverNow >= Date.parse(auction.endAt)) {
    return 'ENDED'
  }

  if (serverNow < Date.parse(auction.startAt)) {
    return 'READY'
  }

  return 'OPEN'
}

function statusLabel(auction, logicalStatus) {
  if (logicalStatus === 'ENDED') {
    if (!auction.finalized) {
      return '종료 · 낙찰 집계 중'
    }

    if (auction.winningBid) {
      return '낙찰 확정'
    }

    if (auction.pendingWinningBidId != null) {
      return '낙찰 결과 확인 중'
    }

    return '유찰'
  }

  return (
    {
      READY: '시작 전',
      OPEN: '진행 중',
      CANCELED: '취소됨',
    }[logicalStatus] ?? '상태 확인 중'
  )
}

function bidBlockReason({
  auction,
  userId,
  signedIn,
  logicalStatus,
  loading,
  loadError,
}) {
  if (loading || loadError) {
    return '최신 경매 상태를 확인해야 입찰할 수 있습니다.'
  }

  if (!signedIn) {
    return '입찰하려면 로그인해야 합니다.'
  }

  if (userId == null) {
    return '로그인 사용자 정보를 확인할 수 없습니다. 다시 로그인해 주세요.'
  }

  if (
    auction.product?.seller?.id != null &&
    String(auction.product.seller.id) === String(userId)
  ) {
    return '판매자 본인은 입찰할 수 없습니다.'
  }

  if (
    auction.leadingBid?.bidder?.id != null &&
    String(auction.leadingBid.bidder.id) === String(userId)
  ) {
    return '현재 최고 입찰자는 다시 입찰할 수 없습니다.'
  }

  if (logicalStatus === 'CANCELED') {
    return '취소된 경매입니다.'
  }

  if (logicalStatus === 'ENDED') {
    return '종료된 경매입니다.'
  }

  if (logicalStatus === 'READY') {
    return '아직 시작하지 않은 경매입니다.'
  }

  if (logicalStatus !== 'OPEN') {
    return '현재 입찰할 수 없는 경매입니다.'
  }

  if (auction.status === 'READY') {
    return '경매가 시작되어 최신 상태를 확인하는 중입니다.'
  }

  if (auction.nextBidAmount == null) {
    return '입찰 가능한 최대 금액에 도달했습니다.'
  }

  return ''
}

function validPrice(value, policy) {
  const amount = Number(value)

  if (
    !/^\d+$/.test(String(value)) ||
    !Number.isSafeInteger(amount) ||
    amount <= 0
  ) {
    return false
  }

  if (!policy) return true

  if (amount < policy.minAmount || amount > policy.maxAmount) {
    return false
  }

  return (
    policy.bands?.some(
      ({ from, to, unit }) =>
        amount >= from &&
        amount <= to &&
        Number.isInteger(unit) &&
        unit > 0 &&
        amount % unit === 0,
    ) ?? false
  )
}

function AuctionDetail() {
  const { id } = useParams()

  const user = useSyncExternalStore(subscribeAuth, getAuthUser, getAuthUser)

  const signedIn = Boolean(getAccessToken())
  const userId = user?.id ?? null

  const [auction, setAuction] = useState(null)
  const [loadError, setLoadError] = useState('')
  const [loading, setLoading] = useState(true)

  const [bidAmount, setBidAmount] = useState('')
  const [bidResult, setBidResult] = useState('')
  const [bidError, setBidError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const [policy, setPolicy] = useState(null)

  const [history, setHistory] = useState(null)
  const [historyError, setHistoryError] = useState('')

  const [page, setPage] = useState(0)
  const [revision, setRevision] = useState(0)
  const [historyRevision, setHistoryRevision] = useState(0)
  const [elapsed, setElapsed] = useState(0)

  const [clock, setClock] = useState({
    serverMs: 0,
    performanceMs: 0,
  })

  const requestBusy = useRef(false)
  const boundaryAttempts = useRef(new Set())
  const bidAmountEdited = useRef(false)

  // REST 응답까지 포함해 가장 큰 version을 보관한다.
  const latestVersion = useRef({
    auctionId: id,
    version: -1,
  })

  function refreshDetail() {
    setLoading(true)
    setRevision((value) => value + 1)
  }

  function refreshHistory() {
    setPage(0)
    setHistoryRevision((value) => value + 1)
  }

  function handleAuctionEvent(event) {
    const version = Number(event.version)

    if (
      !Number.isSafeInteger(version) ||
      version < 0 ||
      String(event.auctionId) !== String(id)
    ) {
      return
    }

    if (latestVersion.current.auctionId !== id) {
      return
    }

    // 이미 REST 또는 WebSocket으로 확인한 버전은 버린다.
    if (version <= latestVersion.current.version) {
      return
    }

    if (
      event.type !== 'AUCTION_PRICE_CHANGED' &&
      event.type !== 'AUCTION_STATUS_CHANGED'
    ) {
      return
    }

    if (!event.data || typeof event.data !== 'object') {
      return
    }

    const data = event.data

    latestVersion.current.version = version

    if (event.type === 'AUCTION_PRICE_CHANGED') {
      setAuction((previous) => {
        if (
          !previous ||
          String(previous.id) !== String(id) ||
          Number(previous.version) >= version
        ) {
          return previous
        }

        return {
          ...previous,
          version,
          currentPrice: data.currentPrice,
          nextBidAmount: data.nextBidAmount,
          bidCount: data.bidCount,
          status: 'OPEN',
          leadingBid: data.leadingBidder
            ? {
                amount: data.currentPrice,
                bidder: data.leadingBidder,
              }
            : null,
        }
      })

      if (!bidAmountEdited.current) {
        setBidAmount(
          data.nextBidAmount == null ? '' : String(data.nextBidAmount),
        )
      }

      refreshHistory()
      return
    }

    if (event.type === 'AUCTION_STATUS_CHANGED') {
      setAuction((previous) => {
        if (
          !previous ||
          String(previous.id) !== String(id) ||
          Number(previous.version) >= version
        ) {
          return previous
        }

        return {
          ...previous,
          version,
          status: data.status,
          finalized: data.finalized,
          endAt: data.endAt ?? previous.endAt,
          pendingWinningBidId: data.winningBidId ?? null,
          nextBidAmount: data.status === 'OPEN' ? previous.nextBidAmount : null,
        }
      })

      // 상세 응답에서 winningBid 전체 정보와 서버 시간을 받는다.
      refreshDetail()
    }
  }

  function handleWebSocketConnected() {
    // 최초 연결과 재연결 모두 REST 기준으로 상태를 맞춘다.
    refreshDetail()
    refreshHistory()
  }

  const connectionStatus = useAuctionRealtime(
    id,
    handleAuctionEvent,
    handleWebSocketConnected,
    userId ?? 'anonymous',
  )

  useEffect(() => {
    const timer = setInterval(() => {
      setElapsed(performance.now())
    }, 1000)

    return () => clearInterval(timer)
  }, [])

  useEffect(() => {
    latestVersion.current = {
      auctionId: id,
      version: -1,
    }

    boundaryAttempts.current.clear()
    bidAmountEdited.current = false
  }, [id])

  // 상세 REST 조회
  useEffect(() => {
    const controller = new AbortController()
    const signal = controller.signal

    async function fetchDetail() {
      try {
        const result = await auctionDetailApi.get(id, signal)

        if (signal.aborted) return

        const receivedAt = performance.now()
        const serverMs = Date.parse(result.serverTime)
        const version = Number(result.version)

        if (!Number.isFinite(serverMs)) {
          throw new Error('서버 시각을 확인할 수 없습니다.')
        }

        if (!Number.isSafeInteger(version)) {
          throw new Error('경매 응답의 version이 올바르지 않습니다.')
        }

        if (latestVersion.current.auctionId !== id) {
          return
        }

        // REST 응답도 최신 WebSocket 이벤트보다 오래됐으면 버린다.
        if (version < latestVersion.current.version) {
          return
        }

        latestVersion.current.version = version

        setClock({
          serverMs,
          performanceMs: receivedAt,
        })

        setElapsed(receivedAt)
        setAuction(result)

        if (!bidAmountEdited.current) {
          setBidAmount(
            result.nextBidAmount == null ? '' : String(result.nextBidAmount),
          )
        }

        setLoadError('')
      } catch (error) {
        if (!signal.aborted) {
          setLoadError(error.message || '경매 상세 조회에 실패했습니다.')
        }
      } finally {
        if (!signal.aborted) {
          setLoading(false)
        }
      }
    }

    void fetchDetail()

    return () => controller.abort()
  }, [id, revision])

  // 서버 시간 기준 시작·종료 경계에서 REST 재조회
  useEffect(() => {
    if (!auction || !clock.serverMs) return undefined

    if (String(auction.id) !== String(id)) {
      return undefined
    }

    const serverNow = clock.serverMs + (performance.now() - clock.performanceMs)

    let boundaryMs = null
    let boundaryName = ''

    if (auction.status === 'READY') {
      boundaryMs = Date.parse(auction.startAt)
      boundaryName = 'START'
    } else if (auction.status === 'OPEN') {
      boundaryMs = Date.parse(auction.endAt)
      boundaryName = 'END'
    }

    if (!Number.isFinite(boundaryMs)) {
      return undefined
    }

    const boundaryKey = `${id}:${boundaryName}:${boundaryMs}`

    if (boundaryAttempts.current.has(boundaryKey)) {
      return undefined
    }

    const timer = setTimeout(
      () => {
        boundaryAttempts.current.add(boundaryKey)
        refreshDetail()
      },
      Math.max(0, boundaryMs - serverNow),
    )

    return () => clearTimeout(timer)
  }, [auction, clock, id])

  // 입찰 이력 REST 조회
  useEffect(() => {
    const controller = new AbortController()

    auctionDetailApi
      .bids(id, page, BID_PAGE_SIZE, controller.signal)
      .then((result) => {
        if (!controller.signal.aborted) {
          setHistory(result)
          setHistoryError('')
        }
      })
      .catch((error) => {
        if (!controller.signal.aborted) {
          setHistory(null)
          setHistoryError(
            error.status === 404
              ? '입찰 이력을 찾을 수 없습니다. API 준비 상태를 확인해 주세요.'
              : error.message || '입찰 이력을 불러오지 못했습니다.',
          )
        }
      })

    return () => controller.abort()
  }, [id, page, revision, historyRevision])

  // 서버 가격단위표
  useEffect(() => {
    const controller = new AbortController()

    auctionDetailApi
      .pricePolicy(controller.signal)
      .then((result) => {
        if (!controller.signal.aborted && Array.isArray(result?.bands)) {
          setPolicy(result)
        }
      })
      .catch(() => {
        // 서버에서 입찰 금액을 최종 검증한다.
      })

    return () => controller.abort()
  }, [])

  const visibleAuction =
    auction && String(auction.id) === String(id) ? auction : null

  const serverNow = visibleAuction
    ? clock.serverMs + (elapsed - clock.performanceMs)
    : 0

  const logicalStatus = getLogicalStatus(visibleAuction, serverNow)

  const untilStart = visibleAuction
    ? Date.parse(visibleAuction.startAt) - serverNow
    : 0

  const untilEnd = visibleAuction
    ? Date.parse(visibleAuction.endAt) - serverNow
    : 0

  const reason = visibleAuction
    ? bidBlockReason({
        auction: visibleAuction,
        userId,
        signedIn,
        logicalStatus,
        loading,
        loadError,
      })
    : ''

  const minimum = visibleAuction?.nextBidAmount
  const amount = Number(bidAmount)

  const validAmount =
    validPrice(bidAmount, policy) && minimum != null && amount >= minimum

  const historyItems = Array.isArray(history?.content) ? history.content : []

  const hasNext =
    history && Number.isInteger(history.totalPages)
      ? page + 1 < history.totalPages
      : historyItems.length === BID_PAGE_SIZE

  async function submitBid(event) {
    event.preventDefault()

    if (
      !visibleAuction ||
      requestBusy.current ||
      loading ||
      reason ||
      !validAmount
    ) {
      return
    }

    const confirmed = window.confirm(
      `${formatPrice(amount)}을(를) 입찰하시겠습니까?\n입찰이 성립하면 철회할 수 없습니다.`,
    )

    if (!confirmed) return

    requestBusy.current = true
    setSubmitting(true)
    setBidResult('')
    setBidError('')

    try {
      const result = await auctionDetailApi.bid(id, amount)

      if (result.resolution === 'OUTBID_BY_AUTO_BID') {
        setBidResult(
          '입찰이 처리됐지만 자동입찰에 의해 최고 입찰자가 되지 못했습니다.',
        )
      } else {
        setBidResult('입찰이 접수됐습니다.')
      }
    } catch (error) {
      setBidError(error.message || '입찰 요청에 실패했습니다.')
    } finally {
      requestBusy.current = false
      bidAmountEdited.current = false
      setSubmitting(false)
      setPage(0)
      refreshDetail()
      refreshHistory()
    }
  }

  if (!/^[1-9]\d*$/.test(String(id ?? ''))) {
    return (
      <Page>
        <FieldError role="alert">올바르지 않은 경매 번호입니다.</FieldError>
      </Page>
    )
  }

  return (
    <Page>
      <Row>
        <Title>경매 상세 #{id}</Title>

        <ConnectionText role="status">
          {CONNECTION_LABELS[connectionStatus]}
        </ConnectionText>

        <Button
          type="button"
          $variant="secondary"
          $size="small"
          onClick={refreshDetail}
          disabled={loading || submitting}
        >
          새로고침
        </Button>
      </Row>

      {loading && <p>경매 정보를 불러오는 중입니다.</p>}

      {loadError && <FieldError role="alert">{loadError}</FieldError>}

      {visibleAuction && (
        <>
          <Panel>
            <Title>{visibleAuction.product?.title || '상품 정보 없음'}</Title>

            {Array.isArray(visibleAuction.product?.images) &&
              visibleAuction.product.images.length > 0 && (
                <Gallery>
                  {visibleAuction.product.images.map((image) => (
                    <Photo
                      key={image.id ?? image.url}
                      src={image.url}
                      alt={`${visibleAuction.product.title} 상품 이미지`}
                    />
                  ))}
                </Gallery>
              )}

            <p>{visibleAuction.product?.description || '상품 설명 없음'}</p>

            <Grid>
              <dt>판매자</dt>
              <dd>{visibleAuction.product?.seller?.nickname || '정보 없음'}</dd>

              <dt>상품 상태</dt>
              <dd>
                {formatProductCondition(visibleAuction.product?.condition)}
              </dd>

              <dt>상세 상태</dt>
              <dd>
                {visibleAuction.product?.conditionDescription || '정보 없음'}
              </dd>

              <dt>지역</dt>
              <dd>
                {visibleAuction.product?.region?.sigunguName || '정보 없음'}
              </dd>

              <dt>경매 상태</dt>
              <dd>{statusLabel(visibleAuction, logicalStatus)}</dd>

              <dt>시작가</dt>
              <dd>{formatPrice(visibleAuction.startPrice)}</dd>

              <dt>현재가</dt>
              <dd>
                <Price>{formatPrice(visibleAuction.currentPrice)}</Price>
              </dd>

              <dt>다음 최소 입찰가</dt>
              <dd>{minimum == null ? '입찰 불가' : formatPrice(minimum)}</dd>

              <dt>입찰 수</dt>
              <dd>{visibleAuction.bidCount}건</dd>

              <dt>현재 선두</dt>
              <dd>{visibleAuction.leadingBid?.bidder?.nickname || '없음'}</dd>

              <dt>시작 시각</dt>
              <dd>{dateLabel(visibleAuction.startAt)}</dd>

              <dt>종료 시각</dt>
              <dd>{dateLabel(visibleAuction.endAt)}</dd>

              <dt>남은 시간</dt>
              <dd>
                <Time>
                  {logicalStatus === 'READY'
                    ? `시작까지 ${formatRemainingTime(untilStart)}`
                    : formatRemainingTime(untilEnd)}
                </Time>
              </dd>

              {logicalStatus === 'ENDED' && visibleAuction.finalized && (
                <>
                  <dt>최종 결과</dt>
                  <dd>
                    {visibleAuction.winningBid
                      ? `${
                          visibleAuction.winningBid.bidder?.nickname || '낙찰자'
                        } · ${formatPrice(visibleAuction.winningBid.amount)}`
                      : visibleAuction.pendingWinningBidId != null
                        ? '낙찰 결과 확인 중'
                        : '유찰'}
                  </dd>
                </>
              )}
            </Grid>
          </Panel>

          <Panel>
            <h3>수동입찰</h3>

            <FieldMessage>
              입찰이 성립하면 철회할 수 없습니다. 가격과 선두 정보는 실시간으로
              갱신됩니다. 최종 입찰 가능 여부는 서버가 판단합니다.
            </FieldMessage>

            {reason && <FieldMessage role="status">{reason}</FieldMessage>}

            {!signedIn && <Link to="/login">로그인하러 가기</Link>}

            <form onSubmit={submitBid}>
              <Field>
                <Label htmlFor="bid-amount">입찰 금액 (원)</Label>

                <Input
                  id="bid-amount"
                  type="number"
                  min={minimum ?? 1}
                  step="1"
                  value={bidAmount}
                  disabled={Boolean(reason) || submitting}
                  onChange={(event) => {
                    bidAmountEdited.current = true
                    setBidAmount(event.target.value)
                  }}
                />

                {minimum != null && (
                  <FieldMessage>
                    최소 {formatPrice(minimum)} · 가격 단위는 서버 정책 기준
                  </FieldMessage>
                )}
              </Field>

              {!reason && bidAmount !== '' && !validAmount && (
                <FieldError role="alert">
                  최소 입찰가 또는 가격단위를 확인해 주세요.
                </FieldError>
              )}

              <Button
                type="submit"
                disabled={Boolean(reason) || !validAmount || submitting}
              >
                {submitting ? '입찰 처리 중...' : '입찰하기'}
              </Button>
            </form>

            {bidResult && (
              <FieldMessage role="status">{bidResult}</FieldMessage>
            )}

            {bidError && <FieldError role="alert">{bidError}</FieldError>}
          </Panel>
        </>
      )}

      <Panel>
        <h3>입찰 이력</h3>

        {historyError && <FieldError role="alert">{historyError}</FieldError>}

        {!historyError && historyItems.length === 0 && (
          <FieldMessage>표시할 입찰 이력이 없습니다.</FieldMessage>
        )}

        {historyItems.length > 0 && (
          <History>
            {historyItems.map((bid) => (
              <li key={bid.id}>
                <strong>{formatPrice(bid.amount)}</strong>
                {' · '}
                {bid.bidder?.nickname || '입찰자'}
                {' · '}
                {dateLabel(bid.createdAt)}
                {bid.type ? ` · ${bid.type}` : ''}
              </li>
            ))}
          </History>
        )}

        <Row>
          <Button
            type="button"
            $variant="secondary"
            $size="small"
            disabled={page === 0}
            onClick={() => setPage((value) => value - 1)}
          >
            이전
          </Button>

          <span>{page + 1}페이지</span>

          <Button
            type="button"
            $variant="secondary"
            $size="small"
            disabled={!hasNext}
            onClick={() => setPage((value) => value + 1)}
          >
            다음
          </Button>
        </Row>
      </Panel>
    </Page>
  )
}

export default AuctionDetail
