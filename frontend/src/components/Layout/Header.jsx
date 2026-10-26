import { useSyncExternalStore } from 'react'
import { Link, useMatch } from 'react-router'
import styled from 'styled-components'
import { getAuthUser, subscribeAuth } from '../../api/client'
import logo from '../../assets/logo.svg'

const Bar = styled.header`
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: ${({ theme }) => theme.layout.headerHeight};
  padding: 0 ${({ theme }) => theme.layout.gutter};
`

const Logo = styled.img`
  display: block;
  height: 24px;
`

const Nickname = styled.span`
  font-size: ${({ theme }) => theme.fontSizes.bodySmall};
  font-weight: ${({ theme }) => theme.fontWeights.semibold};
`

const LoginLink = styled(Link)`
  font-size: ${({ theme }) => theme.fontSizes.bodySmall};
  font-weight: ${({ theme }) => theme.fontWeights.semibold};
  color: ${({ theme }) => theme.colors.primary};
  text-decoration: none;
`

function Header() {
  const user = useSyncExternalStore(subscribeAuth, getAuthUser, getAuthUser)
  const loginMatch = useMatch('/login')
  const signupMatch = useMatch('/signup')
  // 로그인·회원가입 화면에서는 이미 그 화면이라 로그인 버튼을 숨긴다
  const onAuthPage = Boolean(loginMatch || signupMatch)

  return (
    <Bar>
      <Link to="/">
        <Logo src={logo} alt="Layer7 홈" />
      </Link>

      {user?.nickname ? (
        <Nickname>{user.nickname}님</Nickname>
      ) : (
        !onAuthPage && <LoginLink to="/login">로그인</LoginLink>
      )}
    </Bar>
  )
}

export default Header
