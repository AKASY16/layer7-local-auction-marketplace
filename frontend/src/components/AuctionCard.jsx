import styled from 'styled-components'
import {
  formatPrice,
  formatProductCondition,
  formatRemainingTime,
} from '../utils/format'

const Card = styled.article`
  display: flex;
  gap: ${({ theme }) => theme.space.md};
`

// 화면 폭이 375px보다 좁으면 사진 자리를 줄여 현재가·남은 시간이 한 줄에 들어가게 한다
const Thumbnail = styled.div`
  flex: 0 0 28%;
  align-self: flex-start;
  max-width: 96px;
  aspect-ratio: 1;
  overflow: hidden;
  border-radius: ${({ theme }) => theme.radius.control};
  background: ${({ theme }) => theme.colors.cream};
`

const ThumbnailImage = styled.img`
  display: block;
  width: 100%;
  height: 100%;
  object-fit: cover;
`

const Body = styled.div`
  display: flex;
  flex: 1;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.xs};
  min-width: 0;
`

const Title = styled.h3`
  overflow: hidden;
  font-size: ${({ theme }) => theme.fontSizes.cardTitle};
  font-weight: ${({ theme }) => theme.fontWeights.semibold};
  white-space: nowrap;
  text-overflow: ellipsis;
`

const Meta = styled.p`
  font-size: ${({ theme }) => theme.fontSizes.sub};
  color: ${({ theme }) => theme.colors.textSub};
`

// 라벨 줄과 값 줄을 나눠, 크기가 다른 현재가와 남은 시간의 글자 아래쪽을 맞춘다.
// 열 폭을 같게 해서 카드마다 남은 시간 위치가 같다 (금액이 아주 길면 그 카드만 조금 밀린다)
const Stats = styled.dl`
  display: grid;
  grid-template-rows: auto auto;
  grid-auto-columns: 1fr;
  grid-auto-flow: column;
  align-items: baseline;
  column-gap: ${({ theme }) => theme.space.md};
  margin: auto 0 0;
`

const StatLabel = styled.dt`
  font-size: ${({ theme }) => theme.fontSizes.label};
  color: ${({ theme }) => theme.colors.textSub};
`

// "42,000 / 원"처럼 끊기지 않게 값은 한 줄로 둔다
const Price = styled.dd`
  margin: 0;
  white-space: nowrap;
  font-size: ${({ theme }) => theme.fontSizes.priceList};
  font-weight: ${({ theme }) => theme.fontWeights.bold};
  color: ${({ theme }) => theme.colors.primary};
`

const RemainingTime = styled.dd`
  margin: 0;
  white-space: nowrap;
  font-size: ${({ theme }) => theme.fontSizes.bodySmall};
  font-weight: ${({ theme }) => theme.fontWeights.semibold};
  font-variant-numeric: tabular-nums;
  color: ${({ theme }) => theme.colors.danger};
`

// 남은 시간은 화면이 넘겨준 now 기준으로 계산한다 (목록 응답에 serverTime이 없어 브라우저 시각)
function AuctionCard({ auction, now }) {
  const { product } = auction
  const remaining = new Date(auction.endAt).getTime() - now

  return (
    <Card>
      <Thumbnail>
        {product.thumbnailUrl && (
          <ThumbnailImage src={product.thumbnailUrl} alt="" />
        )}
      </Thumbnail>

      <Body>
        <Title>{product.title}</Title>
        <Meta>
          {product.region.sigunguName} ·{' '}
          {formatProductCondition(product.condition)}
        </Meta>

        <Stats>
          <StatLabel>현재가</StatLabel>
          <Price>{formatPrice(auction.currentPrice)}</Price>
          <StatLabel>남은 시간</StatLabel>
          <RemainingTime>{formatRemainingTime(remaining)}</RemainingTime>
        </Stats>
      </Body>
    </Card>
  )
}

export default AuctionCard
