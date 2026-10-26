import { useEffect, useState } from 'react'
import styled from 'styled-components'
import { auctionApi } from '../api/client'
import AuctionCard from '../components/AuctionCard'
import Button from '../components/common/Button'
import { FieldError } from '../components/common/Field'
import useNow from '../hooks/useNow'

const Section = styled.section`
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.lg};
  padding: ${({ theme }) => theme.space.xl} 0;
`

const Heading = styled.div`
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.xs};
`

const Title = styled.h2`
  font-size: ${({ theme }) => theme.fontSizes.title};
  font-weight: ${({ theme }) => theme.fontWeights.bold};
  color: ${({ theme }) => theme.colors.primaryDark};
`

const Description = styled.p`
  font-size: ${({ theme }) => theme.fontSizes.sub};
  color: ${({ theme }) => theme.colors.textSub};
`

const CardList = styled.ul`
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.lg};
  margin: 0;
  padding: 0;
  list-style: none;
`

// 불러오는 중·빈 목록·오류 안내
const Notice = styled.div`
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: ${({ theme }) => theme.space.md};
  padding: ${({ theme }) => theme.space.xl} ${({ theme }) => theme.space.lg};
  border-radius: ${({ theme }) => theme.radius.box};
  background: ${({ theme }) => theme.colors.cream};
  text-align: center;
  font-size: ${({ theme }) => theme.fontSizes.bodySmall};
  color: ${({ theme }) => theme.colors.textSub};
`

function Home() {
  const [auctions, setAuctions] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const [retryCount, setRetryCount] = useState(0)
  const now = useNow()

  useEffect(() => {
    const controller = new AbortController()
    let active = true

    async function loadAuctions() {
      setLoading(true)
      setError(false)

      try {
        // 진행 중 경매의 첫 페이지(최신 등록순 20개). 더 보기는 경매 목록 화면에서 한다
        const response = await auctionApi.search(
          { status: 'OPEN' },
          { signal: controller.signal },
        )

        if (!Array.isArray(response?.content)) {
          throw new Error('경매 목록 형식이 올바르지 않습니다.')
        }

        if (!active) return

        setAuctions(response.content)
      } catch {
        if (!active) return

        setAuctions([])
        setError(true)
      } finally {
        if (active) {
          setLoading(false)
        }
      }
    }

    loadAuctions()

    return () => {
      active = false
      controller.abort()
    }
  }, [retryCount])

  function renderContent() {
    if (loading) {
      return <Notice role="status">경매를 불러오는 중이에요.</Notice>
    }

    if (error) {
      return (
        <Notice>
          <FieldError role="alert">경매 목록을 불러오지 못했어요.</FieldError>
          <Button
            type="button"
            $variant="secondary"
            $size="small"
            onClick={() => setRetryCount((count) => count + 1)}
          >
            다시 불러오기
          </Button>
        </Notice>
      )
    }

    if (auctions.length === 0) {
      return <Notice role="status">지금 진행 중인 경매가 없어요.</Notice>
    }

    return (
      <CardList>
        {auctions.map((auction) => (
          <li key={auction.auctionId}>
            <AuctionCard auction={auction} now={now} />
          </li>
        ))}
      </CardList>
    )
  }

  return (
    <Section>
      <Heading>
        <Title>진행 중 경매</Title>
        <Description>우리 동네의 특별한 중고 경매를 만나보세요</Description>
      </Heading>

      {renderContent()}
    </Section>
  )
}

export default Home
