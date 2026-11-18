import { useEffect, useRef, useState } from 'react'
import { Navigate, useLocation, useNavigate, useParams } from 'react-router'
import styled from 'styled-components'

import { getAccessToken } from '../api/client'
import { auctionCreateApi } from '../api/auctionCreate'
import { getApiErrorMessage } from '../api/errorMessage'
import Button from '../components/common/Button'
import {
  Field,
  FieldError,
  FieldMessage,
  Input,
  Label,
} from '../components/common/Field'
import {
  AuthDescription,
  AuthForm,
  AuthHeading,
  AuthPage,
  AuthTitle,
} from '../components/AuthFormStyles'

const Row = styled.div`
  display: flex;
  gap: ${({ theme }) => theme.space.md};
  flex-wrap: wrap;
`

const ModeButton = styled.button`
  flex: 1 1 120px;
  min-height: 44px;
  border: 1px solid ${({ theme }) => theme.colors.border};
  border-radius: ${({ theme }) => theme.radius.control};
  background: ${({ $selected, theme }) =>
    $selected ? theme.colors.primaryTint : theme.colors.background};
  color: ${({ theme }) => theme.colors.text};
  font-weight: ${({ theme }) => theme.fontWeights.semibold};
  cursor: pointer;

  &:focus-visible {
    outline: 2px solid ${({ theme }) => theme.colors.primary};
    outline-offset: 2px;
  }
`

const Hint = styled.div`
  padding: ${({ theme }) => theme.space.md};
  border-radius: ${({ theme }) => theme.radius.box};
  background: ${({ theme }) => theme.colors.cream};
  color: ${({ theme }) => theme.colors.textSub};
  font-size: ${({ theme }) => theme.fontSizes.bodySmall};
`

const MIN_DURATION_MS = 60 * 60 * 1000
const MAX_DURATION_MS = 7 * 24 * MIN_DURATION_MS

function parseLocalTime(value) {
  if (!value) return null

  const date = new Date(value)

  return Number.isNaN(date.getTime()) ? null : date
}

function priceHint(amountText, policy) {
  if (!policy || amountText === '') return ''

  const amount = Number(amountText)

  if (!Number.isSafeInteger(amount) || amount <= 0) {
    return '시작가는 양의 정수(원)로 입력해 주세요.'
  }

  if (amount < policy.minAmount || amount > policy.maxAmount) {
    return `시작가는 ${policy.minAmount.toLocaleString('ko-KR')}원부터 ${policy.maxAmount.toLocaleString('ko-KR')}원까지 가능합니다.`
  }

  const band = policy.bands.find(
    (item) => amount >= item.from && amount <= item.to,
  )

  if (!band || !Number.isSafeInteger(band.unit) || band.unit <= 0) {
    return '가격 정책을 확인할 수 없습니다. 다시 불러와 주세요.'
  }

  if (amount % band.unit !== 0) {
    return `이 가격 구간은 ${band.unit.toLocaleString('ko-KR')}원 단위입니다.`
  }

  return `유효한 시작가입니다. (현재 구간 ${band.unit.toLocaleString('ko-KR')}원 단위)`
}

function getCreationError(error) {
  if (error?.code === 'AUCTION_PERIOD_INVALID') {
    return '경매 시작·종료 시각이 기간 규칙에 맞지 않습니다. (1시간~7일, 예약 시작은 7일 이내)'
  }

  if (error?.code === 'AMOUNT_LIMIT_EXCEEDED') {
    return '시작가가 서버의 금액 제한을 초과했습니다.'
  }

  if (error?.code === 'INVALID_PRICE_UNIT') {
    return '시작가가 서버 가격단위표에 맞지 않습니다.'
  }

  if (error?.status === 409) {
    return error?.message || '이미 진행 중이거나 예약된 경매가 있는 상품입니다.'
  }

  if (error?.code === 'USER_RESTRICTED') {
    return '경매 생성이 제한된 계정입니다.'
  }

  if (error?.code === 'RESOURCE_NOT_FOUND') {
    return '상품이 존재하지 않거나 사용할 수 없습니다.'
  }

  return getApiErrorMessage(error)
}

function AuctionCreate() {
  const { productId } = useParams()
  const navigate = useNavigate()
  const location = useLocation()

  const submitting = useRef(false)

  const [price, setPrice] = useState('')
  const [startMode, setStartMode] = useState('now')
  const [startInput, setStartInput] = useState('')
  const [endInput, setEndInput] = useState('')

  const [policy, setPolicy] = useState(null)
  const [policyLoading, setPolicyLoading] = useState(true)
  const [policyError, setPolicyError] = useState('')

  const [formError, setFormError] = useState('')
  const [submittingUI, setSubmittingUI] = useState(false)
  const [authExpired, setAuthExpired] = useState(false)
  const [reloadKey, setReloadKey] = useState(0)

  useEffect(() => {
    const controller = new AbortController()

    auctionCreateApi
      .getBidIncrementPolicy(controller.signal)
      .then((result) => {
        if (
          !Number.isSafeInteger(result?.minAmount) ||
          !Number.isSafeInteger(result?.maxAmount) ||
          !Array.isArray(result?.bands) ||
          result.bands.length === 0 ||
          result.bands.some(
            (band) =>
              !Number.isSafeInteger(band.from) ||
              !Number.isSafeInteger(band.to) ||
              !Number.isSafeInteger(band.unit) ||
              band.unit <= 0,
          )
        ) {
          throw new Error('가격 정책 응답 형식이 올바르지 않습니다.')
        }

        if (!controller.signal.aborted) {
          setPolicy(result)
        }
      })
      .catch((error) => {
        if (controller.signal.aborted) return

        setPolicy(null)

        if (error?.status === 401) {
          setAuthExpired(true)
        }

        setPolicyError(error.message || '가격 정책을 불러오지 못했습니다.')
      })
      .finally(() => {
        if (!controller.signal.aborted) {
          setPolicyLoading(false)
        }
      })

    return () => controller.abort()
  }, [reloadKey])

  if (!getAccessToken() || authExpired) {
    return <Navigate to="/login" state={{ from: location.pathname }} replace />
  }

  const amountHint = priceHint(price, policy)

  const amountIsValid =
    Boolean(policy) &&
    price !== '' &&
    Number.isSafeInteger(Number(price)) &&
    Number(price) >= policy.minAmount &&
    Number(price) <= policy.maxAmount &&
    policy.bands.some(
      ({ from, to, unit }) =>
        Number(price) >= from &&
        Number(price) <= to &&
        Number(price) % unit === 0,
    )

  async function handleSubmit(event) {
    event.preventDefault()

    if (submitting.current) return

    setFormError('')

    if (!/^\d+$/.test(String(productId || '')) || Number(productId) <= 0) {
      setFormError('올바른 상품 번호가 필요합니다.')
      return
    }

    if (!policy || !amountIsValid) {
      setFormError('가격단위표에 맞는 시작가를 입력해 주세요.')
      return
    }

    const now = Date.now()

    const effectiveStart =
      startMode === 'reserved' ? parseLocalTime(startInput) : new Date(now)

    const end = parseLocalTime(endInput)

    if (!effectiveStart || !end) {
      setFormError('시작 시각과 종료 시각을 확인해 주세요.')
      return
    }

    if (startMode === 'reserved' && effectiveStart.getTime() <= now) {
      setFormError('예약 시작 시각은 현재보다 미래여야 합니다.')
      return
    }

    if (
      startMode === 'reserved' &&
      effectiveStart.getTime() > now + MAX_DURATION_MS
    ) {
      setFormError('예약 시작은 현재로부터 7일 이내여야 합니다.')
      return
    }

    const duration = end.getTime() - effectiveStart.getTime()

    if (duration < MIN_DURATION_MS || duration > MAX_DURATION_MS) {
      setFormError('경매 진행 기간은 1시간 이상, 7일 이하여야 합니다.')
      return
    }

    submitting.current = true
    setSubmittingUI(true)

    try {
      const created = await auctionCreateApi.create(productId, {
        startPrice: Number(price),
        startAt: startMode === 'reserved' ? effectiveStart.toISOString() : null,
        endAt: end.toISOString(),
      })

      if (!created?.id) {
        throw new Error('경매 생성 응답에 경매 번호가 없습니다.')
      }

      navigate(`/auctions/${created.id}`, {
        replace: true,
      })
    } catch (error) {
      if (error?.status === 401) {
        setAuthExpired(true)
      }

      setFormError(getCreationError(error))
    } finally {
      submitting.current = false
      setSubmittingUI(false)
    }
  }

  return (
    <AuthPage>
      <AuthHeading>
        <AuthTitle>일반 경매 생성</AuthTitle>

        <AuthDescription>
          상품 #{productId} · 시작가와 경매 일정을 설정해 주세요.
        </AuthDescription>
      </AuthHeading>

      <Hint>
        일반 경매는 1시간~7일 동안 진행할 수 있습니다. 예약 시작은 7일 이내여야
        하며, 최종 유효성은 서버에서 판단합니다. 타임 경매는 현재 지원하지
        않습니다.
      </Hint>

      <AuthForm onSubmit={handleSubmit}>
        <Field>
          <Label htmlFor="auction-start-price">시작가 (원)</Label>

          <Input
            id="auction-start-price"
            type="number"
            min="1"
            step="1"
            inputMode="numeric"
            value={price}
            onChange={(event) => setPrice(event.target.value)}
            placeholder="시작가를 입력해 주세요"
            required
            aria-describedby="start-price-hint"
          />

          {policyLoading ? (
            <FieldMessage>가격단위표를 불러오는 중입니다.</FieldMessage>
          ) : policyError ? (
            <>
              <FieldError role="alert">{policyError}</FieldError>

              <Button
                type="button"
                $variant="secondary"
                $size="small"
                onClick={() => {
                  setPolicyLoading(true)
                  setPolicyError('')
                  setReloadKey((value) => value + 1)
                }}
              >
                가격 정책 다시 불러오기
              </Button>
            </>
          ) : (
            <FieldMessage id="start-price-hint" role="status">
              {amountHint || '서버 가격단위표에 맞는 금액을 입력해 주세요.'}
            </FieldMessage>
          )}
        </Field>

        <Field>
          <Label>시작 시각</Label>

          <Row>
            <ModeButton
              type="button"
              $selected={startMode === 'now'}
              aria-pressed={startMode === 'now'}
              onClick={() => setStartMode('now')}
            >
              즉시 시작
            </ModeButton>

            <ModeButton
              type="button"
              $selected={startMode === 'reserved'}
              aria-pressed={startMode === 'reserved'}
              onClick={() => setStartMode('reserved')}
            >
              예약 시작
            </ModeButton>
          </Row>
        </Field>

        {startMode === 'reserved' && (
          <Field>
            <Label htmlFor="auction-start-at">예약 시작 시각</Label>

            <Input
              id="auction-start-at"
              type="datetime-local"
              value={startInput}
              onChange={(event) => setStartInput(event.target.value)}
              required
            />

            <FieldMessage>현재 시각 이후부터 7일 이내</FieldMessage>
          </Field>
        )}

        <Field>
          <Label htmlFor="auction-end-at">종료 시각</Label>

          <Input
            id="auction-end-at"
            type="datetime-local"
            value={endInput}
            onChange={(event) => setEndInput(event.target.value)}
            required
          />

          <FieldMessage>
            입력한 시각은 브라우저의 현지 시간으로 해석해 서버에 UTC로
            전송합니다.
          </FieldMessage>
        </Field>

        {formError && <FieldError role="alert">{formError}</FieldError>}

        <Button
          type="submit"
          disabled={submittingUI || !policy || !amountIsValid}
        >
          {submittingUI ? '경매 생성 중...' : '경매 생성'}
        </Button>
      </AuthForm>
    </AuthPage>
  )
}

export default AuctionCreate
