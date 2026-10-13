const API_BASE_URL = '/api/v1' // API 요청 시 사용하는 기본 경로 apifetch("/auth/login"); -> /api/v1/auth/login

// Access Token은 메모리에만 보관한다.
let accessToken = null // 페이지 새로 고침 시 초기화

export function setAccessToken(token) {
  accessToken = typeof token === 'string' && token ? token : null
} // 토큰이 문자열이고 비어있지 않으면 accessToken에 저장, 아니면 null로 초기화

export function getAccessToken() {
  return accessToken
}

export function clearAccessToken() {
  accessToken = null
} // 로그아웃 or 인증 정보 초기화 시 사용

// 공통 API 요청 함수
export async function apiFetch(path, options = {}) {
  if (typeof path !== 'string' || !path.startsWith('/')) {
    throw new Error('API 경로는 /로 시작해야 합니다.')
  }

  const { body, headers: customHeaders, ...restOptions } = options
  const headers = new Headers(customHeaders || {})

  headers.set('Accept', 'application/json')

  const isFormData = typeof FormData !== 'undefined' && body instanceof FormData

  if (body !== undefined && body !== null && !isFormData) {
    if (!headers.has('Content-Type')) {
      headers.set('Content-Type', 'application/json')
    }
  }

  if (accessToken) {
    headers.set('Authorization', `Bearer ${accessToken}`)
  }

  let response

  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...restOptions,
      headers,
      credentials: 'include',
      body:
        body === undefined || body === null
          ? undefined
          : isFormData
            ? body
            : typeof body === 'string'
              ? body
              : JSON.stringify(body),
    })
  } catch {
    const error = new Error(
      '서버에 연결할 수 없습니다. 네트워크를 확인해주세요.',
    )
    error.code = 'NETWORK_ERROR'
    error.status = 0
    error.fieldErrors = []
    throw error
  }

  if (response.status === 204) {
    if (!response.ok) {
      const error = new Error('요청을 처리하지 못했습니다.')
      error.status = response.status
      error.code = 'UNKNOWN_ERROR'
      error.fieldErrors = []
      throw error
    }
    return null
  }

  const contentType = response.headers.get('content-type') || ''
  let result = null

  if (contentType.includes('application/json')) {
    try {
      result = await response.json()
    } catch {
      result = null
    }
  } else {
    result = await response.text()
  }

  if (!response.ok) {
    const errorBody = result && typeof result === 'object' ? result : {}

    const error = new Error(errorBody.message || '요청을 처리하지 못했습니다.')

    error.status = response.status
    error.code = errorBody.code || 'UNKNOWN_ERROR'
    error.fieldErrors = Array.isArray(errorBody.fieldErrors)
      ? errorBody.fieldErrors
      : []
    error.path = errorBody.path || null
    error.traceId = errorBody.traceId || null

    throw error
  }

  return result
}

// 인증 API
export const authApi = {
  async login({ email, password }) {
    const data = await apiFetch('/auth/login', {
      method: 'POST',
      body: { email, password },
    })

    if (!data?.accessToken) {
      const error = new Error('로그인 응답에 Access Token이 없습니다.')
      error.code = 'INVALID_RESPONSE'
      error.status = 200
      error.fieldErrors = []
      throw error
    }

    setAccessToken(data.accessToken)
    return data
  },

  async signup({ email, password, nickname, regionId }) {
    return apiFetch('/auth/signup', {
      method: 'POST',
      body: { email, password, nickname, regionId },
    })
  },

  async logout() {
    try {
      return await apiFetch('/auth/logout', {
        method: 'POST',
      })
    } finally {
      clearAccessToken()
    }
  },
}

// TODO: 다음 스프린트에서 Refresh Token 자동 갱신 구현
