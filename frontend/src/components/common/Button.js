import styled, { css } from 'styled-components'

// $variant: primary(와인색 채움, 기본) | secondary(테두리만)
const variants = {
  primary: css`
    border: 1px solid ${({ theme }) => theme.colors.primary};
    background: ${({ theme }) => theme.colors.primary};
    color: ${({ theme }) => theme.colors.onPrimary};
  `,
  secondary: css`
    border: 1px solid ${({ theme }) => theme.colors.border};
    background: ${({ theme }) => theme.colors.background};
    color: ${({ theme }) => theme.colors.text};
  `,
}

// $size: medium(폼 제출 같은 주요 동작, 기본) | small(다시 불러오기 같은 보조 동작)
const sizes = {
  medium: css`
    min-height: 52px;
    padding: 0 ${({ theme }) => theme.space.lg};
    font-size: ${({ theme }) => theme.fontSizes.cardTitle};
  `,
  small: css`
    min-height: 40px;
    padding: 0 ${({ theme }) => theme.space.md};
    font-size: ${({ theme }) => theme.fontSizes.bodySmall};
  `,
}

const Button = styled.button`
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: ${({ theme }) => theme.radius.control};
  font-weight: ${({ theme }) => theme.fontWeights.semibold};
  cursor: pointer;
  ${({ $variant = 'primary' }) => variants[$variant]}
  ${({ $size = 'medium' }) => sizes[$size]}

  &:focus-visible {
    outline: 2px solid ${({ theme }) => theme.colors.primary};
    outline-offset: 2px;
  }

  &:disabled {
    cursor: not-allowed;
    opacity: 0.6;
  }
`

export default Button
