import { useSyncExternalStore } from 'react'
import styled from 'styled-components'
import { getAuthUser, subscribeAuth } from '../../api/client'

const Nickname = styled.span`
  display: inline-block;
  font-size: 1rem;
  font-weight: 600;
  color: ${({ theme }) => theme.colors?.text || '#24212b'};
`

function Header({ title }) {
  const user = useSyncExternalStore(subscribeAuth, getAuthUser, getAuthUser)

  return (
    <header>
      <h1>{title}</h1>
      {user?.nickname && <Nickname>{user.nickname}님</Nickname>}
    </header>
  )
}

export default Header
