import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router'
import styled from 'styled-components'

import { auctionApi } from '../api/client'
import AuctionCard from './AuctionCard'
import Button from './common/Button'
import { FieldError } from './common/Field'
import useNow from '../hooks/useNow'

const CATEGORIES = [
  ['DIGITAL', '디지털'],
  ['HOME_APPLIANCE', '생활가전'],
  ['FURNITURE', '가구'],
  ['LIVING_KITCHEN', '생활·주방'],
  ['FASHION', '패션'],
  ['BEAUTY', '뷰티'],
  ['SPORTS_LEISURE', '스포츠·레저'],
  ['HOBBY_GAME', '취미·게임'],
  ['BOOK_MEDIA', '도서·미디어'],
  ['ETC', '기타'],
]

const Container = styled.section`
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.lg};
  padding: ${({ theme }) => theme.space.lg} 0 ${({ theme }) => theme.space.xl};
`

const SearchForm = styled.form`
  display: flex;
  align-items: center;
  gap: ${({ theme }) => theme.space.sm};
  padding: 0 ${({ theme }) => theme.space.md};
  border: 1px solid ${({ theme }) => theme.colors.beige};
  border-radius: ${({ theme }) => theme.radius.control};
  min-height: 44px;

  &:focus-within {
    border-color: ${({ theme }) => theme.colors.primary};
  }
`

const SearchIcon = styled.span`
  color: ${({ theme }) => theme.colors.primary};
  font-size: ${({ theme }) => theme.fontSizes.cardTitle};
`

const SearchInput = styled.input`
  flex: 1;
  min-width: 0;
  border: 0;
  outline: none;
  background: transparent;
  color: ${({ theme }) => theme.colors.text};
  font-size: ${({ theme }) => theme.fontSizes.bodySmall};

  &::placeholder {
    color: ${({ theme }) => theme.colors.textSub};
  }
`

const SearchButton = styled.button`
  border: 0;
  background: transparent;
  color: ${({ theme }) => theme.colors.primary};
  font-size: ${({ theme }) => theme.fontSizes.bodySmall};
  font-weight: ${({ theme }) => theme.fontWeights.semibold};
  cursor: pointer;
`

const Tabs = styled.div`
  display: flex;
  gap: ${({ theme }) => theme.space.xs};
  align-items: center;
  flex-wrap: wrap;
`

const Chip = styled.button`
  min-height: 34px;
  padding: 0 ${({ theme }) => theme.space.md};
  border-radius: ${({ theme }) => theme.radius.pill};
  border: 1px solid
    ${({ theme, $active }) =>
      $active ? theme.colors.primary : theme.colors.border};
  background: ${({ theme, $active }) =>
    $active ? theme.colors.primary : theme.colors.background};
  color: ${({ theme, $active }) =>
    $active ? theme.colors.onPrimary : theme.colors.text};
  font-size: ${({ theme }) => theme.fontSizes.label};
  cursor: pointer;

  &:disabled {
    opacity: 0.55;
    cursor: not-allowed;
  }
`

const FilterPanel = styled.div`
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.sm};
  padding: ${({ theme }) => theme.space.md};
  background: ${({ theme }) => theme.colors.cream};
  border-radius: ${({ theme }) => theme.radius.box};
`

const CategorySelect = styled.select`
  width: 100%;
  min-height: 44px;
  padding: 0 ${({ theme }) => theme.space.md};
  border: 1px solid ${({ theme }) => theme.colors.border};
  border-radius: ${({ theme }) => theme.radius.control};
  background: ${({ theme }) => theme.colors.background};
  color: ${({ theme }) => theme.colors.text};
`

const Heading = styled.div`
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: ${({ theme }) => theme.space.sm};
`

const Title = styled.h2`
  font-size: ${({ theme }) => theme.fontSizes.title};
  font-weight: ${({ theme }) => theme.fontWeights.bold};
  color: ${({ theme }) => theme.colors.primaryDark};
`

const MoreLink = styled(Link)`
  flex-shrink: 0;
  color: ${({ theme }) => theme.colors.primary};
  font-size: ${({ theme }) => theme.fontSizes.label};
  text-decoration: none;
`

const Description = styled.p`
  color: ${({ theme }) => theme.colors.textSub};
  font-size: ${({ theme }) => theme.fontSizes.sub};
`

const List = styled.ul`
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.lg};
  padding: 0;
  margin: 0;
  list-style: none;
`

const CardLink = styled(Link)`
  display: block;
  text-decoration: none;

  &:focus-visible {
    outline: 2px solid ${({ theme }) => theme.colors.primary};
    outline-offset: 3px;
  }
`

const Notice = styled.div`
  padding: ${({ theme }) => theme.space.xl};
  background: ${({ theme }) => theme.colors.cream};
  border-radius: ${({ theme }) => theme.radius.box};
  text-align: center;
  color: ${({ theme }) => theme.colors.textSub};
  font-size: ${({ theme }) => theme.fontSizes.bodySmall};
`

const Pagination = styled.div`
  display: flex;
  justify-content: center;
  align-items: center;
  gap: ${({ theme }) => theme.space.md};
`

function AuctionExplorer({ compact = false }) {
  const [params, setParams] = useSearchParams()

  const [keywordInput, setKeywordInput] = useState(params.get('keyword') || '')
  const [mode, setMode] = useState('open')
  const [showFilter, setShowFilter] = useState(false)

  const [auctions, setAuctions] = useState([])
  const [totalPages, setTotalPages] = useState(1)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [retry, setRetry] = useState(0)

  const now = useNow()

  const keyword = params.get('keyword') || ''
  const regionId = params.get('regionId') || ''
  const regionLabel = params.get('regionLabel') || ''
  const category = params.get('category') || ''
  const page = compact ? 0 : Math.max(0, Number(params.get('page')) || 0)

  const query = params.toString()

  // 주소창 검색 조건이 바뀌면 입력창도 동기화
  useEffect(() => {
    setKeywordInput(keyword)
  }, [keyword])

  // 검색 조건 변경
  function updateQuery(changes) {
    const next = new URLSearchParams(params)

    Object.entries(changes).forEach(([key, value]) => {
      if (value === '' || value === null) {
        next.delete(key)
      } else {
        next.set(key, String(value))
      }
    })

    if (!Object.hasOwn(changes, 'page')) {
      next.delete('page')
    }

    setParams(next)
  }

  // 실제 API에서 지원하는 조건으로 조회
  useEffect(() => {
    const controller = new AbortController()
    let active = true

    async function load() {
      setLoading(true)
      setError('')

      try {
        const response = await auctionApi.search(
          {
            status: 'OPEN',
            keyword: keyword || undefined,
            regionId: regionId || undefined,
            category: category || undefined,
            page,
            size: 20,
          },
          { signal: controller.signal },
        )

        if (!Array.isArray(response?.content)) {
          throw new Error('경매 목록 응답 형식이 올바르지 않습니다.')
        }

        if (!active) return

        setAuctions(response.content)
        setTotalPages(Math.max(1, response.totalPages || 1))
      } catch {
        if (!active || controller.signal.aborted) return

        setAuctions([])
        setError('경매 목록을 불러오지 못했습니다.')
      } finally {
        if (active) setLoading(false)
      }
    }

    load()

    return () => {
      active = false
      controller.abort()
    }
  }, [query, page, keyword, regionId, category, retry])

  // 마감 임박은 현재 조회한 페이지 안에서만 정렬
  const displayedAuctions =
    mode === 'ending'
      ? [...auctions].sort(
          (a, b) => new Date(a.endAt).getTime() - new Date(b.endAt).getTime(),
        )
      : auctions

  function submitSearch(event) {
    event.preventDefault()
    updateQuery({ keyword: keywordInput.trim().slice(0, 100) })
  }

  return (
    <Container>
      <SearchForm role="search" onSubmit={submitSearch}>
        <SearchIcon aria-hidden="true">⌕</SearchIcon>

        <SearchInput
          value={keywordInput}
          onChange={(event) => setKeywordInput(event.target.value)}
          placeholder="원하는 중고 상품을 검색해보세요"
          aria-label="상품 검색어"
          maxLength={100}
        />

        <SearchButton type="submit">검색</SearchButton>
      </SearchForm>

      <Tabs aria-label="경매 탐색 옵션">
        <Chip
          type="button"
          $active={mode === 'open'}
          onClick={() => setMode('open')}
        >
          ◷ 진행 중
        </Chip>

        <Chip
          type="button"
          $active={mode === 'ending'}
          onClick={() => setMode('ending')}
        >
          ♨ 마감 임박
        </Chip>

        <Chip type="button" disabled title="관심도 정렬 API 연결 후 제공">
          ▥ 관심 많은 순
        </Chip>

        <Chip
          type="button"
          $active={showFilter}
          onClick={() => setShowFilter((old) => !old)}
          aria-expanded={showFilter}
        >
          ▽ 필터
        </Chip>
      </Tabs>

      {showFilter && (
        <FilterPanel>
          <label htmlFor="auction-category">카테고리</label>

          <CategorySelect
            id="auction-category"
            value={category}
            onChange={(event) => updateQuery({ category: event.target.value })}
          >
            <option value="">전체 카테고리</option>

            {CATEGORIES.map(([code, label]) => (
              <option key={code} value={code}>
                {label}
              </option>
            ))}
          </CategorySelect>

          <Button
            type="button"
            $variant="secondary"
            $size="small"
            onClick={() => updateQuery({ category: '', keyword: '' })}
          >
            검색·카테고리 초기화
          </Button>
        </FilterPanel>
      )}

      <div>
        <Heading>
          <Title>
            {regionLabel ? `${regionLabel} 진행 중 경매` : '진행 중 경매'}
          </Title>

          {compact && (
            <MoreLink to={`/auctions${query ? `?${query}` : ''}`}>
              전체보기 ›
            </MoreLink>
          )}
        </Heading>

        <Description>
          안녕하세요. 우리 동네의 특별한 경매를 만나보세요.
        </Description>

        {mode === 'ending' && (
          <Description>마감 임박순은 현재 불러온 목록 기준입니다.</Description>
        )}
      </div>

      {loading ? (
        <Notice role="status">경매를 불러오는 중입니다.</Notice>
      ) : error ? (
        <Notice>
          <FieldError role="alert">{error}</FieldError>
          <Button
            type="button"
            $variant="secondary"
            $size="small"
            onClick={() => setRetry((value) => value + 1)}
          >
            다시 불러오기
          </Button>
        </Notice>
      ) : displayedAuctions.length === 0 ? (
        <Notice role="status">조건에 맞는 진행 중 경매가 없습니다.</Notice>
      ) : (
        <List>
          {displayedAuctions.map((auction) => (
            <li key={auction.auctionId}>
              <CardLink
                to={`/auctions/${auction.auctionId}`}
                aria-label={`${auction.product.title} 상세 보기`}
              >
                <AuctionCard auction={auction} now={now} />
              </CardLink>
            </li>
          ))}
        </List>
      )}

      {!compact && !loading && !error && totalPages > 1 && (
        <Pagination>
          <Button
            type="button"
            $variant="secondary"
            $size="small"
            disabled={page === 0}
            onClick={() => updateQuery({ page: page - 1 })}
          >
            이전
          </Button>

          <Description>
            {page + 1} / {totalPages}
          </Description>

          <Button
            type="button"
            $variant="secondary"
            $size="small"
            disabled={page >= totalPages - 1}
            onClick={() => updateQuery({ page: page + 1 })}
          >
            다음
          </Button>
        </Pagination>
      )}
    </Container>
  )
}

export default AuctionExplorer
