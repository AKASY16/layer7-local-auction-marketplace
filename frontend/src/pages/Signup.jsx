import { useState } from 'react'
import { Link, useNavigate } from 'react-router'
import { authApi } from '../api/client'
import { getApiErrorMessage } from '../api/errorMessage'

function Signup() {
  const navigate = useNavigate()

  const [form, setForm] = useState({
    email: '',
    password: '',
    passwordConfirm: '',
    nickname: '',
    regionId: '',
  })

  const [errorMessage, setErrorMessage] = useState('')
  const [loading, setLoading] = useState(false)

  function handleChange(event) {
    const { name, value } = event.target

    setForm((previous) => ({
      ...previous,
      [name]: value,
    }))
  }

  async function handleSubmit(event) {
    event.preventDefault()
    setErrorMessage('')

    if (
      !form.email.trim() ||
      !form.password ||
      !form.nickname.trim() ||
      !form.regionId
    ) {
      setErrorMessage('모든 항목을 입력해 주세요.')
      return
    }

    if (form.password !== form.passwordConfirm) {
      setErrorMessage('비밀번호가 일치하지 않습니다.')
      return
    }

    const regionId = Number(form.regionId)

    if (!Number.isInteger(regionId) || regionId <= 0) {
      setErrorMessage('올바른 지역 ID를 입력해 주세요.')
      return
    }

    setLoading(true)

    try {
      await authApi.signup({
        email: form.email.trim(),
        password: form.password,
        nickname: form.nickname.trim(),
        regionId,
      })

      alert('회원가입이 완료되었습니다.')
      navigate('/login')
    } catch (error) {
      setErrorMessage(getApiErrorMessage(error))
    } finally {
      setLoading(false)
    }
  }

  return (
    <main>
      <h2>회원가입</h2>

      <form onSubmit={handleSubmit}>
        <div>
          <label htmlFor="email">이메일</label>
          <input
            id="email"
            name="email"
            type="email"
            value={form.email}
            onChange={handleChange}
            autoComplete="email"
            required
          />
        </div>

        <div>
          <label htmlFor="password">비밀번호</label>
          <input
            id="password"
            name="password"
            type="password"
            value={form.password}
            onChange={handleChange}
            autoComplete="new-password"
            required
          />
        </div>

        <div>
          <label htmlFor="passwordConfirm">비밀번호 확인</label>
          <input
            id="passwordConfirm"
            name="passwordConfirm"
            type="password"
            value={form.passwordConfirm}
            onChange={handleChange}
            autoComplete="new-password"
            required
          />
        </div>

        <div>
          <label htmlFor="nickname">닉네임</label>
          <input
            id="nickname"
            name="nickname"
            type="text"
            value={form.nickname}
            onChange={handleChange}
            autoComplete="nickname"
            required
          />
        </div>

        <div>
          <label htmlFor="regionId">지역 ID</label>
          <input
            id="regionId"
            name="regionId"
            type="number"
            min="1"
            value={form.regionId}
            onChange={handleChange}
            required
          />
        </div>

        {errorMessage && (
          <p role="alert" style={{ color: 'red' }}>
            {errorMessage}
          </p>
        )}

        <button type="submit" disabled={loading}>
          {loading ? '가입 중...' : '회원가입'}
        </button>
      </form>

      <p>
        이미 계정이 있나요? <Link to="/login">로그인</Link>
      </p>
    </main>
  )
}

export default Signup
