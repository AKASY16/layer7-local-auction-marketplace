import { createGlobalStyle } from 'styled-components'

const GlobalStyle = createGlobalStyle`
  /* 목업이 흰 화면 기준이라 OS가 다크 모드여도 밝은 화면으로 고정한다 */
  :root {
    color-scheme: light;
  }

  *,
  *::before,
  *::after {
    box-sizing: border-box;
  }

  body {
    margin: 0;
    background: ${({ theme }) => theme.colors.background};
    color: ${({ theme }) => theme.colors.text};
    font-family: ${({ theme }) => theme.fonts.body};
    font-size: ${({ theme }) => theme.fontSizes.body};
    line-height: 1.5;
    -webkit-font-smoothing: antialiased;
  }

  h1,
  h2,
  h3,
  p {
    margin: 0;
  }

  button,
  input,
  select,
  textarea {
    font: inherit;
  }

  a {
    color: inherit;
  }
`

export default GlobalStyle
