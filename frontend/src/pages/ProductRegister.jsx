import { useEffect, useRef, useState } from 'react'
import { Navigate, useLocation } from 'react-router'
import styled from 'styled-components'

import { clearAccessToken, getAccessToken } from '../api/client'
import { getApiErrorMessage } from '../api/errorMessage'
import {
  productApi,
  putProductImage,
  requestProductImageUpload,
} from '../api/product'

import Button from '../components/common/Button'
import {
  Field,
  FieldError,
  FieldMessage,
  Input,
  Label,
  Select,
} from '../components/common/Field'
import {
  AuthDescription,
  AuthForm,
  AuthPage,
  AuthTitle,
} from '../components/AuthFormStyles'
import { CATEGORIES } from '../constants/categories'

// 이미지 형식 및 개수 제한
const ACCEPTED_TYPES = new Set(['image/jpeg', 'image/png', 'image/webp'])

const MAX_IMAGES = 10
const MAX_BYTES = 10 * 1024 * 1024

// 서버 입력 글자 수 제한
const MAX_TITLE_LENGTH = 120
const MAX_DESCRIPTION_LENGTH = 10000
const MAX_CONDITION_DESCRIPTION_LENGTH = 500

// 상품 상태
const CONDITIONS = [
  ['UNOPENED', '미개봉'],
  ['LIKE_NEW', '거의 새 상품'],
  ['GOOD', '양호'],
  ['FAIR', '사용감 있음'],
  ['DAMAGED', '손상 있음'],
  ['NEEDS_REPAIR', '수리 필요'],
]

// 이미지 목록 디자인
const ImageGrid = styled.ul`
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: ${({ theme }) => theme.space.md};
  padding: 0;
  margin: 0;
  list-style: none;
`

const ImageItem = styled.li`
  min-width: 0;
  padding: ${({ theme }) => theme.space.sm};
  border: 1px solid ${({ theme }) => theme.colors.border};
  border-radius: ${({ theme }) => theme.radius.control};
  overflow-wrap: anywhere;
`

const Thumbnail = styled.img`
  display: block;
  width: 100%;
  aspect-ratio: 1;
  object-fit: cover;
  border-radius: ${({ theme }) => theme.radius.control};
  margin-bottom: ${({ theme }) => theme.space.sm};
`

const Description = styled.textarea`
  width: 100%;
  min-height: 112px;
  padding: ${({ theme }) => theme.space.md};
  border: 1px solid ${({ theme }) => theme.colors.border};
  border-radius: ${({ theme }) => theme.radius.control};
  background: ${({ theme }) => theme.colors.background};
  color: ${({ theme }) => theme.colors.text};
  resize: vertical;

  &:focus-visible {
    outline: 2px solid ${({ theme }) => theme.colors.primary};
  }
`

const Notice = styled.section`
  padding: ${({ theme }) => theme.space.lg};
  border-radius: ${({ theme }) => theme.radius.box};
  background: ${({ theme }) => theme.colors.cream};
  display: grid;
  gap: ${({ theme }) => theme.space.md};
`

const ButtonRow = styled.div`
  display: flex;
  flex-wrap: wrap;
  gap: ${({ theme }) => theme.space.sm};

  & > button {
    flex: 1 1 auto;
  }
`

const HiddenHelp = styled.span`
  color: ${({ theme }) => theme.colors.textSub};
  font-size: ${({ theme }) => theme.fontSizes.sub};
`

function ProductRegister() {
  const location = useLocation()

  // 현재 Access Token 존재 여부
  const authenticated = Boolean(getAccessToken())

  const mounted = useRef(true)
  const controller = useRef(null)
  const filesRef = useRef([])
  const busy = useRef(false)

  // 선택한 이미지
  const [files, setFiles] = useState([])

  // 상품 입력 정보
  const [form, setForm] = useState({
    title: '',
    description: '',
    category: '',
    condition: '',
    conditionDescription: '',
  })

  const [busyUI, setBusyUI] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState(null)
  const [imageViewError, setImageViewError] = useState('')
  const [authExpired, setAuthExpired] = useState(false)

  // 이미지 목록 상태 갱신
  function updateFiles(fn) {
    const next = fn(filesRef.current)
    filesRef.current = next

    if (mounted.current) {
      setFiles(next)
    }
  }

  // 화면을 벗어날 때 요청 및 미리보기 정리
  useEffect(() => {
    mounted.current = true

    return () => {
      mounted.current = false
      controller.current?.abort()

      filesRef.current.forEach((entry) => {
        URL.revokeObjectURL(entry.preview)
      })
    }
  }, [])

  // 이미지 선택
  function handleFiles(event) {
    const incoming = Array.from(event.target.files || [])
    event.target.value = ''

    if (!incoming.length) return

    if (filesRef.current.length + incoming.length > MAX_IMAGES) {
      setError(`이미지는 최대 ${MAX_IMAGES}장까지 등록할 수 있습니다.`)
      return
    }

    const invalid = incoming.find(
      (file) =>
        !ACCEPTED_TYPES.has(file.type) ||
        file.size > MAX_BYTES ||
        file.size === 0,
    )

    if (invalid) {
      setError(
        `${invalid.name}: JPEG/PNG/WebP 파일만 가능하며, 한 장당 10MB 이하여야 합니다.`,
      )
      return
    }

    setError('')

    updateFiles((old) =>
      old.concat(
        incoming.map((file) => ({
          id: crypto.randomUUID(),
          file,
          preview: URL.createObjectURL(file),
          status: 'ready',
          progress: 0,
          error: '',
          objectKey: null,
        })),
      ),
    )
  }

  // 이미지 제외
  function removeFile(id) {
    if (busy.current) return

    const entry = filesRef.current.find((item) => item.id === id)

    if (entry) {
      URL.revokeObjectURL(entry.preview)
    }

    updateFiles((old) => old.filter((item) => item.id !== id))
  }

  // 이미지 한 장 업로드
  async function uploadOne(entry, signal) {
    updateFiles((old) =>
      old.map((item) =>
        item.id === entry.id
          ? {
              ...item,
              status: 'uploading',
              progress: 0,
              error: '',
            }
          : item,
      ),
    )

    try {
      // 재시도 때마다 새로운 업로드 URL 발급
      const upload = await requestProductImageUpload(entry.file, signal)

      const key = await putProductImage(
        entry.file,
        upload,
        (progress) => {
          updateFiles((old) =>
            old.map((item) =>
              item.id === entry.id ? { ...item, progress } : item,
            ),
          )
        },
        signal,
      )

      updateFiles((old) =>
        old.map((item) =>
          item.id === entry.id
            ? {
                ...item,
                status: 'uploaded',
                progress: 100,
                objectKey: key,
              }
            : item,
        ),
      )

      return true
    } catch (cause) {
      if (signal.aborted) return false

      if (cause?.status === 401 || cause?.code === 'INVALID_TOKEN') {
        clearAccessToken()
        if (mounted.current) setAuthExpired(true)
      }

      updateFiles((old) =>
        old.map((item) =>
          item.id === entry.id
            ? {
                ...item,
                status: 'failed',
                error: getApiErrorMessage(cause),
              }
            : item,
        ),
      )

      return false
    }
  }

  // 실패한 이미지만 다시 업로드
  async function retryUpload(id) {
    if (busy.current) return

    const entry = filesRef.current.find((item) => item.id === id)

    if (!entry || entry.status !== 'failed') return

    busy.current = true
    setBusyUI(true)
    controller.current = new AbortController()

    try {
      await uploadOne(entry, controller.current.signal)
    } finally {
      busy.current = false
      if (mounted.current) setBusyUI(false)
    }
  }

  // 상품 등록
  async function handleSubmit(event) {
    event.preventDefault()

    if (busy.current || success) return

    // 필수 입력값 확인
    if (
      !form.title.trim() ||
      !form.description.trim() ||
      !form.category ||
      !form.condition ||
      !form.conditionDescription.trim()
    ) {
      setError('모든 상품 정보를 입력해 주세요.')
      return
    }

    // 서버의 문자열 길이 제한을 업로드 전에 검사
    if (
      form.title.trim().length > MAX_TITLE_LENGTH ||
      form.description.trim().length > MAX_DESCRIPTION_LENGTH ||
      form.conditionDescription.trim().length > MAX_CONDITION_DESCRIPTION_LENGTH
    ) {
      setError('상품 정보의 글자 수 제한을 확인해 주세요.')
      return
    }

    if (!filesRef.current.length) {
      setError('상품 이미지를 1장 이상 선택해 주세요.')
      return
    }

    setError('')
    busy.current = true
    setBusyUI(true)

    controller.current = new AbortController()
    const signal = controller.current.signal

    try {
      // 모든 이미지 업로드
      for (const entry of filesRef.current) {
        if (signal.aborted) return

        const current = filesRef.current.find((item) => item.id === entry.id)

        if (current?.status === 'uploaded') continue

        const ok = await uploadOne(entry, signal)

        if (!ok) {
          setError(
            '이미지 업로드에 실패했습니다. 실패한 이미지만 다시 업로드한 후 등록해 주세요.',
          )
          return
        }
      }

      // 업로드 완료된 이미지 키 확인
      const imageKeys = filesRef.current.map((item) => item.objectKey)

      if (imageKeys.some((key) => !key)) return

      // 상품 등록 API 호출
      const created = await productApi.create(
        {
          category: form.category,
          title: form.title.trim(),
          description: form.description.trim(),
          condition: form.condition,
          conditionDescription: form.conditionDescription.trim(),
          imageKeys,
        },
        signal,
      )

      if (!created?.id) {
        throw new Error('상품 등록 응답에 상품 ID가 없습니다.')
      }

      // 상품 등록 성공
      setSuccess(created)

      // 등록된 상품 이미지 재조회
      try {
        const detail = await productApi.get(created.id, signal)

        if (mounted.current && String(detail?.id) === String(created.id)) {
          setSuccess(detail)
        }
      } catch {
        if (mounted.current) {
          setImageViewError(
            '상품은 등록됐지만 서버 이미지 조회를 확인하지 못했습니다.',
          )
        }
      }
    } catch (cause) {
      if (!signal.aborted && mounted.current) {
        if (cause?.status === 401 || cause?.code === 'INVALID_TOKEN') {
          clearAccessToken()
          setAuthExpired(true)
        } else {
          setError(getApiErrorMessage(cause))
        }
      }
    } finally {
      busy.current = false
      if (mounted.current) setBusyUI(false)
    }
  }

  // 비로그인 사용자
  if (!authenticated || authExpired) {
    return <Navigate to="/login" state={{ from: location.pathname }} replace />
  }

  // 등록 완료 화면
  if (success) {
    return (
      <AuthPage>
        <AuthTitle>상품 등록 완료</AuthTitle>

        <Notice role="status">
          <strong>{success.title}</strong>
          <p>{success.description}</p>
          <FieldMessage>상품 번호: {success.id}</FieldMessage>

          {Array.isArray(success.images) && success.images.length > 0 ? (
            <ImageGrid>
              {success.images.map((image) => (
                <ImageItem key={image.id || image.url}>
                  <Thumbnail
                    src={image.url}
                    alt={`${success.title} 상품 이미지`}
                  />
                </ImageItem>
              ))}
            </ImageGrid>
          ) : (
            <FieldMessage>이미지 주소 확인이 필요합니다.</FieldMessage>
          )}

          {imageViewError && (
            <FieldError role="alert">{imageViewError}</FieldError>
          )}

          <Button
            type="button"
            disabled
            title="경매 생성 화면은 이슈 #87에서 구현합니다."
          >
            경매 생성 (준비 중)
          </Button>

          <HiddenHelp>
            상품 등록은 완료되었습니다. 경매 생성은 후속 이슈 #87에서
            연결합니다.
          </HiddenHelp>
        </Notice>
      </AuthPage>
    )
  }

  // 상품 등록 입력 화면
  return (
    <AuthPage>
      <AuthTitle>상품 등록</AuthTitle>

      <AuthDescription>
        상품 정보를 입력하고 사진을 1~10장 등록해 주세요.
      </AuthDescription>

      <AuthForm onSubmit={handleSubmit}>
        <Field>
          <Label htmlFor="product-title">상품 제목</Label>
          <Input
            id="product-title"
            value={form.title}
            disabled={busyUI}
            required
            maxLength={MAX_TITLE_LENGTH}
            onChange={(event) =>
              setForm((old) => ({
                ...old,
                title: event.target.value,
              }))
            }
          />
        </Field>

        <Field>
          <Label htmlFor="product-description">상품 설명</Label>
          <Description
            id="product-description"
            value={form.description}
            disabled={busyUI}
            required
            maxLength={MAX_DESCRIPTION_LENGTH}
            onChange={(event) =>
              setForm((old) => ({
                ...old,
                description: event.target.value,
              }))
            }
          />
        </Field>

        <Field>
          <Label htmlFor="product-category">카테고리</Label>
          <Select
            id="product-category"
            value={form.category}
            disabled={busyUI}
            required
            onChange={(event) =>
              setForm((old) => ({
                ...old,
                category: event.target.value,
              }))
            }
          >
            <option value="">카테고리를 선택하세요</option>

            {CATEGORIES.map(([code, label]) => (
              <option key={code} value={code}>
                {label}
              </option>
            ))}
          </Select>
        </Field>

        <Field>
          <Label htmlFor="product-condition">상품 상태</Label>
          <Select
            id="product-condition"
            value={form.condition}
            disabled={busyUI}
            required
            onChange={(event) =>
              setForm((old) => ({
                ...old,
                condition: event.target.value,
              }))
            }
          >
            <option value="">상품 상태를 선택하세요</option>

            {CONDITIONS.map(([code, label]) => (
              <option key={code} value={code}>
                {label}
              </option>
            ))}
          </Select>
        </Field>

        <Field>
          <Label htmlFor="condition-description">상태 상세 설명</Label>
          <Description
            id="condition-description"
            value={form.conditionDescription}
            disabled={busyUI}
            required
            maxLength={MAX_CONDITION_DESCRIPTION_LENGTH}
            onChange={(event) =>
              setForm((old) => ({
                ...old,
                conditionDescription: event.target.value,
              }))
            }
          />
        </Field>

        <Field>
          <Label htmlFor="product-images">상품 이미지</Label>

          <Input
            id="product-images"
            type="file"
            accept="image/jpeg,image/png,image/webp"
            multiple
            disabled={busyUI || files.length >= MAX_IMAGES}
            onChange={handleFiles}
          />

          <FieldMessage>JPEG·PNG·WebP / 장당 10MB 이하 / 1~10장</FieldMessage>

          <ImageGrid>
            {files.map((entry) => (
              <ImageItem key={entry.id}>
                <Thumbnail
                  src={entry.preview}
                  alt={`${entry.file.name} 미리보기`}
                />

                <FieldMessage>{entry.file.name}</FieldMessage>

                <FieldMessage>
                  {entry.status === 'uploading'
                    ? `업로드 중 ${entry.progress}%`
                    : entry.status === 'uploaded'
                      ? '업로드 완료'
                      : entry.status === 'failed'
                        ? '업로드 실패'
                        : '업로드 대기'}
                </FieldMessage>

                {entry.status === 'uploading' && (
                  <progress
                    value={entry.progress}
                    max="100"
                    aria-label={`${entry.file.name} 업로드 진행률`}
                  />
                )}

                {entry.error && (
                  <FieldError role="alert">{entry.error}</FieldError>
                )}

                <ButtonRow>
                  {entry.status === 'failed' && (
                    <Button
                      type="button"
                      $variant="secondary"
                      $size="small"
                      onClick={() => retryUpload(entry.id)}
                      disabled={busyUI}
                    >
                      다시 업로드
                    </Button>
                  )}

                  <Button
                    type="button"
                    $variant="secondary"
                    $size="small"
                    onClick={() => removeFile(entry.id)}
                    disabled={busyUI}
                  >
                    제외
                  </Button>
                </ButtonRow>
              </ImageItem>
            ))}
          </ImageGrid>
        </Field>

        {error && <FieldError role="alert">{error}</FieldError>}

        <Button type="submit" disabled={busyUI}>
          {busyUI ? '업로드·등록 중...' : '상품 등록'}
        </Button>
      </AuthForm>
    </AuthPage>
  )
}

export default ProductRegister
