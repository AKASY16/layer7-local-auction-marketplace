import { createGlobalStyle } from 'styled-components'

const GlobalStyle = createGlobalStyle`
  *,
  *::before,
  *::after {
    box-sizing: border-box;
  }

  body {
    margin: 0;
    font-family:
      system-ui,
      -apple-system,
      'Apple SD Gothic Neo',
      'Malgun Gothic',
      sans-serif;
    line-height: 1.5;
  }
`

export default GlobalStyle
