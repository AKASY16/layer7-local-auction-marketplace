import { useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router'
import { authApi } from '../api/client'
import { getApiErrorMessage } from '../api/errorMessage'
import RegionSelector from '../components/RegionSelector'

import {
  AuthPage,
  AuthHeading,
  AuthTitle,
  AuthForm,
  AuthSwitch,
} from '../components/AuthFormStyles'
import Button from '../components/common/Button'
import { Field, Label, Input, FieldError } from '../components/common/Field'

function Signup() {
  const navigate = useNavigate()
  const submitting = useRef(false)

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

  // 지역 선택 컴포넌트에서 선택한 ID 저장
  function handleRegionChange(regionId) {
    setForm((previous) => ({
      ...previous,
      regionId,
    }))
  }

  async function handleSubmit(event) {
    event.preventDefault()

    if (submitting.current) return

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
      setErrorMessage('올바른 지역을 선택해 주세요.')
      return
    }

    submitting.current = true
    setLoading(true)

    try {
      await authApi.signup({
        email: form.email.trim(),
        password: form.password,
        nickname: form.nickname.trim(),
        regionId,
      })

      alert('회원가입이 완료되었습니다.')
      navigate('/login') //회원가입 후 로그인 페이지로 이동
    } catch (error) {
      setErrorMessage(getApiErrorMessage(error))
    } finally {
      submitting.current = false
      setLoading(false)
    }
  }

  return (
    <AuthPage>
      <AuthHeading>
        <AuthTitle>회원가입</AuthTitle>
      </AuthHeading>

      <AuthForm onSubmit={handleSubmit}>
        <Field>
          <Label htmlFor="email">이메일</Label>
          <Input
            id="email"
            name="email"
            type="email"
            value={form.email}
            onChange={handleChange}
            autoComplete="email"
            required
          />
        </Field>

        <Field>
          <Label htmlFor="password">비밀번호</Label>
          <Input
            id="password"
            name="password"
            type="password"
            value={form.password}
            onChange={handleChange}
            autoComplete="new-password"
            required
          />
        </Field>

        <Field>
          <Label htmlFor="passwordConfirm">비밀번호 확인</Label>
          <Input
            id="passwordConfirm"
            name="passwordConfirm"
            type="password"
            value={form.passwordConfirm}
            onChange={handleChange}
            autoComplete="new-password"
            required
          />
        </Field>

        <Field>
          <Label htmlFor="nickname">닉네임</Label>
          <Input
            id="nickname"
            name="nickname"
            type="text"
            value={form.nickname}
            onChange={handleChange}
            autoComplete="nickname"
            required
          />
        </Field>

        {/* 지역 ID 입력 대신 지역 선택 컴포넌트 사용 */}
        <RegionSelector
          value={form.regionId}
          onChange={handleRegionChange}
          disabled={loading}
        />

        {errorMessage && <FieldError role="alert">{errorMessage}</FieldError>}

        <Button type="submit" disabled={loading}>
          {loading ? '가입 중...' : '회원가입'}
        </Button>
      </AuthForm>

      <AuthSwitch>
        이미 계정이 있나요?<Link to="/login">로그인</Link>
      </AuthSwitch>
    </AuthPage>
  )
}

export default Signup
