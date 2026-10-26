import styled from 'styled-components'

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

// 경매 목록 화면이 들어올 자리 (별도 작업)
const Placeholder = styled.p`
  padding: ${({ theme }) => theme.space.xl} ${({ theme }) => theme.space.lg};
  border-radius: ${({ theme }) => theme.radius.box};
  background: ${({ theme }) => theme.colors.cream};
  text-align: center;
  font-size: ${({ theme }) => theme.fontSizes.bodySmall};
  color: ${({ theme }) => theme.colors.textSub};
`

function Home() {
  return (
    <Section>
      <Heading>
        <Title>진행 중 경매</Title>
        <Description>우리 동네의 특별한 중고 경매를 만나보세요</Description>
      </Heading>

      <Placeholder>경매 목록은 준비 중이에요.</Placeholder>
    </Section>
  )
}

export default Home
