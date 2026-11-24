import { useEffect, useRef, useState, useSyncExternalStore } from 'react'
import { Link, useParams } from 'react-router'
import styled from 'styled-components'

import { getAccessToken, getAuthUser, subscribeAuth } from '../api/client'
import { auctionDetailApi } from '../api/auctionDetail'
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

    return auction.winningBid ? '낙찰 확정' : '유찰'
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

  // 예약 경매 시작 시각 이후에는 최신 OPEN 응답이 필요하다.
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
  const [elapsed, setElapsed] = useState(0)

  const [clock, setClock] = useState({
    serverMs: 0,
    performanceMs: 0,
  })

  const requestBusy = useRef(false)
  const boundaryAttempts = useRef(new Set())

  // OS 시각 변경과 독립적으로 카운트다운 갱신
  useEffect(() => {
    const timer = setInterval(() => {
      setElapsed(performance.now())
    }, 1000)

    return () => clearInterval(timer)
  }, [])

  // 최신 경매 상세 조회
  useEffect(() => {
    const controller = new AbortController()
    const signal = controller.signal

    async function fetchDetail() {
      try {
        const result = await auctionDetailApi.get(id, signal)

        if (signal.aborted) return

        const receivedAt = performance.now()
        const serverMs = Date.parse(result.serverTime)

        if (!Number.isFinite(serverMs)) {
          throw new Error('서버 시각을 확인할 수 없습니다.')
        }

        setClock({
          serverMs,
          performanceMs: receivedAt,
        })

        setElapsed(receivedAt)
        setAuction(result)

        setBidAmount(
          result.nextBidAmount == null ? '' : String(result.nextBidAmount),
        )

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

  // 서버 시간 기준 시작·종료 경계에서 상세를 자동 재조회한다.
  // WebSocket이나 지속적인 API 폴링은 사용하지 않는다.
  useEffect(() => {
    if (!auction || !clock.serverMs) return undefined

    const serverNow = clock.serverMs + (performance.now() - clock.performanceMs)

    const startMs = Date.parse(auction.startAt)
    const endMs = Date.parse(auction.endAt)

    let boundaryMs = null
    let boundaryName = ''

    if (auction.status === 'READY') {
      boundaryMs = startMs
      boundaryName = 'START'
    } else if (auction.status === 'OPEN') {
      boundaryMs = endMs
      boundaryName = 'END'
    }

    if (!Number.isFinite(boundaryMs)) return undefined

    const boundaryKey = `${id}:${boundaryName}:${boundaryMs}`

    if (boundaryAttempts.current.has(boundaryKey)) {
      return undefined
    }

    const remainingMs = boundaryMs - serverNow

    const timer = setTimeout(
      () => {
        boundaryAttempts.current.add(boundaryKey)

        setLoading(true)
        setRevision((value) => value + 1)
      },
      Math.max(0, remainingMs),
    )

    return () => clearTimeout(timer)
  }, [auction, clock, id])

  // 입찰 이력
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
  }, [id, page, revision])

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
        // 조회 실패 시 서버의 최종 금액 검증을 사용한다.
      })

    return () => controller.abort()
  }, [])

  const serverNow = auction
    ? clock.serverMs + (elapsed - clock.performanceMs)
    : 0

  const logicalStatus = getLogicalStatus(auction, serverNow)

  const untilStart = auction ? Date.parse(auction.startAt) - serverNow : 0

  const untilEnd = auction ? Date.parse(auction.endAt) - serverNow : 0

  const reason = auction
    ? bidBlockReason({
        auction,
        userId,
        signedIn,
        logicalStatus,
        loading,
        loadError,
      })
    : ''

  const minimum = auction?.nextBidAmount
  const amount = Number(bidAmount)

  const validAmount =
    validPrice(bidAmount, policy) && minimum != null && amount >= minimum

  const historyItems = Array.isArray(history?.content) ? history.content : []

  const hasNext =
    history && Number.isInteger(history.totalPages)
      ? page + 1 < history.totalPages
      : historyItems.length === BID_PAGE_SIZE

  function refreshDetail() {
    setLoading(true)
    setRevision((value) => value + 1)
  }

  async function submitBid(event) {
    event.preventDefault()

    if (!auction || requestBusy.current || loading || reason || !validAmount) {
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
      // 서버가 제공한 구체적인 거절 이유를 표시
      setBidError(error.message || '입찰 요청에 실패했습니다.')
    } finally {
      requestBusy.current = false
      setSubmitting(false)

      setPage(0)
      refreshDetail()
    }
  }

  if (!/^\d+$/.test(String(id || '')) || Number(id) <= 0) {
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

      {auction && (
        <>
          <Panel>
            <Title>{auction.product?.title || '상품 정보 없음'}</Title>

            {Array.isArray(auction.product?.images) &&
              auction.product.images.length > 0 && (
                <Gallery>
                  {auction.product.images.map((image) => (
                    <Photo
                      key={image.id ?? image.url}
                      src={image.url}
                      alt={`${auction.product.title} 상품 이미지`}
                    />
                  ))}
                </Gallery>
              )}

            <p>{auction.product?.description || '상품 설명 없음'}</p>

            <Grid>
              <dt>판매자</dt>
              <dd>{auction.product?.seller?.nickname || '정보 없음'}</dd>

              <dt>상품 상태</dt>
              <dd>{formatProductCondition(auction.product?.condition)}</dd>

              <dt>상세 상태</dt>
              <dd>{auction.product?.conditionDescription || '정보 없음'}</dd>

              <dt>지역</dt>
              <dd>{auction.product?.region?.sigunguName || '정보 없음'}</dd>

              <dt>경매 상태</dt>
              <dd>{statusLabel(auction, logicalStatus)}</dd>

              <dt>시작가</dt>
              <dd>{formatPrice(auction.startPrice)}</dd>

              <dt>현재가</dt>
              <dd>
                <Price>{formatPrice(auction.currentPrice)}</Price>
              </dd>

              <dt>다음 최소 입찰가</dt>
              <dd>{minimum == null ? '입찰 불가' : formatPrice(minimum)}</dd>

              <dt>입찰 수</dt>
              <dd>{auction.bidCount}건</dd>

              <dt>현재 선두</dt>
              <dd>{auction.leadingBid?.bidder?.nickname || '없음'}</dd>

              <dt>시작 시각</dt>
              <dd>{dateLabel(auction.startAt)}</dd>

              <dt>종료 시각</dt>
              <dd>{dateLabel(auction.endAt)}</dd>

              <dt>남은 시간</dt>
              <dd>
                <Time>
                  {logicalStatus === 'READY'
                    ? `시작까지 ${formatRemainingTime(untilStart)}`
                    : formatRemainingTime(untilEnd)}
                </Time>
              </dd>

              {logicalStatus === 'ENDED' && auction.finalized && (
                <>
                  <dt>최종 결과</dt>
                  <dd>
                    {auction.winningBid
                      ? `${
                          auction.winningBid.bidder?.nickname || '낙찰자'
                        } · ${formatPrice(auction.winningBid.amount)}`
                      : '유찰'}
                  </dd>
                </>
              )}
            </Grid>
          </Panel>

          <Panel>
            <h3>수동입찰</h3>

            <FieldMessage>
              입찰이 성립하면 철회할 수 없습니다. 실시간 갱신은 제공하지
              않으므로 다른 사용자의 입찰은 새로고침 후 확인해 주세요.
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
                  onChange={(event) => setBidAmount(event.target.value)}
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
