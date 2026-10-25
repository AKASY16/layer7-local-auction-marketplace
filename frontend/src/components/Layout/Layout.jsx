import { Outlet } from 'react-router'
import styled from 'styled-components'
import Header from './Header'

// 목업이 휴대폰 화면 기준이라 PC에서는 가운데 일정 폭으로 보여준다
const Shell = styled.div`
  max-width: ${({ theme }) => theme.layout.maxWidth};
  min-height: 100vh;
  margin: 0 auto;
  background: ${({ theme }) => theme.colors.background};

  @media (min-width: ${({ theme }) => theme.layout.maxWidth}) {
    border-inline: 1px solid ${({ theme }) => theme.colors.border};
  }
`

const Main = styled.main`
  padding: 0 ${({ theme }) => theme.layout.gutter};
`

function Layout() {
  return (
    <Shell>
      <Header />

      <Main>
        <Outlet />
      </Main>
    </Shell>
  )
}

export default Layout
