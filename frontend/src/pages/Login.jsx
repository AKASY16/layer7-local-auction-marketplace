import { useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router'
import { authApi } from '../api/client'
import { getApiErrorMessage } from '../api/errorMessage'
import {
  AuthPage,
  AuthPanel,
  AuthForm,
  AuthField,
  AuthLabel,
  AuthInput,
  AuthButton,
  AuthError,
} from '../components/AuthFormStyles'

function Login() {
  const navigate = useNavigate()
  const submitting = useRef(false)

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [errorMessage, setErrorMessage] = useState('')
  const [isLoading, setIsLoading] = useState(false)

  async function handleSubmit(event) {
    event.preventDefault()
    if (submitting.current) return
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

    submitting.current = true
    setIsLoading(true)

    try {
      await authApi.login({ email: trimmedEmail, password })

      navigate('/', { replace: true })
    } catch (error) {
      setErrorMessage(getApiErrorMessage(error))
    } finally {
      submitting.current = false
      setIsLoading(false)
    }
  }

  return (
    <AuthPage>
      <AuthPanel>
        <h2>로그인</h2>
        <p>Layer7 Auction에 오신 것을 환영합니다.</p>

        <AuthForm onSubmit={handleSubmit}>
          <AuthField>
            <AuthLabel htmlFor="email">이메일</AuthLabel>
            <AuthInput
              id="email"
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              placeholder="이메일을 입력해 주세요"
              autoComplete="email"
              required
            />
          </AuthField>

          <AuthField>
            <AuthLabel htmlFor="password">비밀번호</AuthLabel>
            <AuthInput
              id="password"
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              placeholder="비밀번호를 입력해 주세요"
              autoComplete="current-password"
              required
            />
          </AuthField>

          {errorMessage && (
            <AuthError role="alert">{errorMessage}</AuthError>
          )}

          <AuthButton type="submit" disabled={isLoading}>
            {isLoading ? '로그인 중...' : '로그인'}
          </AuthButton>
        </AuthForm>

        <p>
          아직 회원이 아니신가요? <Link to="/signup">회원가입</Link>
        </p>
      </AuthPanel>
    </AuthPage>
  )
}

export default Login
