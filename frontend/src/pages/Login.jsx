import { useState } from 'react'
import { Link, useNavigate } from 'react-router'
import { authApi } from '../api/client'
import { getApiErrorMessage } from '../api/errorMessage'

const USE_MOCK_LOGIN = true

function Login() {
  const navigate = useNavigate()

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [errorMessage, setErrorMessage] = useState('')
  const [isLoading, setIsLoading] = useState(false)

  async function handleSubmit(event) {
    event.preventDefault()
    setErrorMessage('')

    const trimmedEmail = email.trim()

    if (!trimmedEmail || !password) {
      setErrorMessage('이메일과 비밀번호를 모두 입력해 주세요.')
      return
    }

    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(trimmedEmail)) {
      setErrorMessage('올바른 이메일 형식을 입력해 주세요.')
      return
    }
    // 정규식을 이용하여 이메일 형식 검증(정규식/.test(trimmedEmail) : 정규식과 일치하는지 검사)
    // [^\s@]+ : 공백과 @ 문자를 제외한 1개 이상의 문자
    // @ : @ 문자
    // \.: . 문자 (정규식에서 .은 모든 문자를 의미, 따라서 .을 문자 그대로 인식시키기 위해 \를 붙임, 마침표가 포함되어있는지 검사)
    // $ : 끝까지 검사

    setIsLoading(true)

    try {
      if (USE_MOCK_LOGIN) {
        // 백엔드 연결 전 화면 흐름 확인용 임시 로그인
        const mockUser = {
          email: trimmedEmail,
          nickname: trimmedEmail.split('@')[0],
        }

        sessionStorage.setItem('layer7MockUser', JSON.stringify(mockUser))
      } else {
        // 실제 API 연결 시 사용
        await authApi.login({
          email: trimmedEmail,
          password,
        })
      }

      navigate('/', { replace: true })
    } catch (error) {
      setErrorMessage(getApiErrorMessage(error))
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <main className="login-page">
      <section className="login-container">
        <h2>로그인</h2>
        <p>Layer7 Auction에 오신 것을 환영합니다.</p>

        <form onSubmit={handleSubmit}>
          <div>
            <label htmlFor="email">이메일</label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              placeholder="이메일을 입력해 주세요"
              autoComplete="email"
              required
            />
          </div>

          <div>
            <label htmlFor="password">비밀번호</label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              placeholder="비밀번호를 입력해 주세요"
              autoComplete="current-password"
              required
            />
          </div>

          {errorMessage && (
            <p role="alert" className="login-error">
              {errorMessage}
            </p>
          )}

          <button type="submit" disabled={isLoading}>
            {isLoading ? '로그인 중...' : '로그인'}
          </button>
        </form>

        <p>
          아직 회원이 아니신가요? <Link to="/signup">회원가입</Link>
        </p>
      </section>
    </main>
  )
}

export default Login
