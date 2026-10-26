import styled from 'styled-components'

// 로그인·회원가입 화면 틀. 입력칸·버튼은 components/common의 공통 부품을 쓴다
export const AuthPage = styled.section`
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.xl};
  padding: ${({ theme }) => theme.space.xl} 0 40px;
`

export const AuthHeading = styled.div`
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.xs};
`

export const AuthTitle = styled.h2`
  font-size: ${({ theme }) => theme.fontSizes.title};
  font-weight: ${({ theme }) => theme.fontWeights.bold};
  color: ${({ theme }) => theme.colors.primaryDark};
`

export const AuthDescription = styled.p`
  font-size: ${({ theme }) => theme.fontSizes.bodySmall};
  color: ${({ theme }) => theme.colors.textSub};
`

export const AuthForm = styled.form`
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.lg};
`

// "이미 계정이 있나요? 로그인"처럼 다른 화면으로 넘어가는 안내
export const AuthSwitch = styled.p`
  text-align: center;
  font-size: ${({ theme }) => theme.fontSizes.bodySmall};
  color: ${({ theme }) => theme.colors.textSub};

  a {
    margin-left: ${({ theme }) => theme.space.xs};
    color: ${({ theme }) => theme.colors.primary};
    font-weight: ${({ theme }) => theme.fontWeights.semibold};
    text-decoration: none;
  }
`
