import styled, { css } from 'styled-components'

export const Field = styled.div`
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.sm};
`

export const Label = styled.label`
  font-size: ${({ theme }) => theme.fontSizes.bodySmall};
  font-weight: ${({ theme }) => theme.fontWeights.semibold};
`

// 입력칸과 선택칸이 같이 쓰는 모양
const controlStyle = css`
  width: 100%;
  min-height: 48px;
  padding: 0 ${({ theme }) => theme.space.md};
  border: 1px solid ${({ theme }) => theme.colors.border};
  border-radius: ${({ theme }) => theme.radius.control};
  background: ${({ theme }) => theme.colors.background};
  color: ${({ theme }) => theme.colors.text};

  &::placeholder {
    color: ${({ theme }) => theme.colors.textSub};
  }

  &:focus-visible {
    outline: none;
    border-color: ${({ theme }) => theme.colors.primary};
    box-shadow: 0 0 0 3px ${({ theme }) => theme.colors.primaryTint};
  }

  &:disabled {
    background: ${({ theme }) => theme.colors.disabled};
    color: ${({ theme }) => theme.colors.textSub};
    cursor: not-allowed;
  }
`

export const Input = styled.input`
  ${controlStyle}
`

export const Select = styled.select`
  ${controlStyle}
`

export const FieldMessage = styled.p`
  font-size: ${({ theme }) => theme.fontSizes.sub};
  color: ${({ theme }) => theme.colors.textSub};
`

// 목업의 경고 문구처럼 와인색 굵게 쓴다 (빨강은 남은 시간 전용)
export const FieldError = styled.p`
  font-size: ${({ theme }) => theme.fontSizes.bodySmall};
  font-weight: ${({ theme }) => theme.fontWeights.semibold};
  color: ${({ theme }) => theme.colors.primary};
`
