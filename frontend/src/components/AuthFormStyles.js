import styled from 'styled-components'

export const AuthPage = styled.main`
  display: flex;
  justify-content: center;
  padding: 40px 20px;
`

export const AuthPanel = styled.section`
  width: 100%;
  max-width: 440px;
  text-align: left;

  h2 {
    text-align: center;
  }

  > p {
    margin: 12px 0 20px;
    text-align: center;
  }
`

export const AuthForm = styled.form`
  display: flex;
  flex-direction: column;
  gap: 16px;
`

export const AuthField = styled.div`
  display: flex;
  flex-direction: column;
  gap: 6px;
`

export const AuthLabel = styled.label`
  font-weight: 600;
`

export const AuthInput = styled.input`
  width: 100%;
  min-height: 42px;
  border: 1px solid #9c9ca6;
  border-radius: 8px;
  padding: 8px 12px;
  font: inherit;
  background: #fff;
  color: #24212b;

  &:focus-visible {
    outline: 2px solid ${({ theme }) => theme.colors?.primary || '#8766bd'};
    outline-offset: 2px;
  }
`

export const AuthButton = styled.button`
  min-height: 44px;
  padding: 10px 16px;
  border: 0;
  border-radius: 8px;
  background: ${({ theme }) => theme.colors?.primary || '#c3a3ee'};
  color: #24212b;
  font: inherit;
  font-weight: 600;
  cursor: pointer;

  &:disabled {
    cursor: wait;
    opacity: 0.65;
  }
`

export const AuthError = styled.p`
  color: #b42318;
  font-size: 0.9rem;
`
