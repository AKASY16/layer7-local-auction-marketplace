const API_BASE_URL = "/api/v1";

// Access Token은 메모리에만 보관한다.
let accessToken = null;

// 토큰이 문자열이고 비어 있지 않으면 저장하고,
// 그렇지 않으면 null로 초기화한다.
export function setAccessToken(token) {
  accessToken = typeof token === "string" && token ? token : null;
}

export function getAccessToken() {
  return accessToken;
}

// 로그아웃 또는 인증 정보 초기화 시 사용한다.
export function clearAccessToken() {
  accessToken = null;
}

// 공통 API 요청 함수
export async function apiFetch(path, options = {}) {
  if (typeof path !== "string" || !path.startsWith("/")) {
    throw new Error("API 경로는 /로 시작해야 합니다.");
  }

  const { body, headers: customHeaders, ...restOptions } = options;
  const headers = new Headers(customHeaders || {});

  headers.set("Accept", "application/json");

  // FormData는 브라우저가 Content-Type을 설정하도록 둔다.
  const isFormData =
    typeof FormData !== "undefined" && body instanceof FormData;

  if (body !== undefined && body !== null && !isFormData) {
    if (!headers.has("Content-Type")) {
      headers.set("Content-Type", "application/json");
    }
  }

  // Access Token이 있을 때만 인증 헤더를 추가한다.
  if (accessToken) {
    headers.set("Authorization", `Bearer ${accessToken}`);
  }

  let response;

  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...restOptions,
      headers,
      credentials: "include",
      body:
        body === undefined || body === null
          ? undefined
          : isFormData
            ? body
            : typeof body === "string"
              ? body
              : JSON.stringify(body),
    });
  } catch {
    // 네트워크 연결 실패 처리
    const error = new Error(
      "서버에 연결할 수 없습니다. 네트워크를 확인해 주세요.",
    );

    error.code = "NETWORK_ERROR";
    error.status = 0;
    error.fieldErrors = [];

    throw error;
  }

  // 응답 본문이 없는 경우
  if (response.status === 204) {
    if (!response.ok) {
      const error = new Error("요청을 처리하지 못했습니다.");
      error.status = response.status;
      error.code = "UNKNOWN_ERROR";
      error.fieldErrors = [];
      throw error;
    }
    return null;
  }

  // 응답 형식에 따라 본문을 읽는다.
  const contentType = response.headers.get("content-type") || "";
  let result = null;

  if (contentType.includes("application/json")) {
    try {
      result = await response.json();
    } catch {
      result = null;
    }
  } else {
    result = await response.text();
  }

  // HTTP 오류 응답 처리
  if (!response.ok) {
    const errorBody = result && typeof result === "object" ? result : {};

    const error = new Error(errorBody.message || "요청을 처리하지 못했습니다.");

    error.status = response.status;
    error.code = errorBody.code || "UNKNOWN_ERROR";
    error.fieldErrors = Array.isArray(errorBody.fieldErrors)
      ? errorBody.fieldErrors
      : [];
    error.path = errorBody.path || null;
    error.traceId = errorBody.traceId || null;

    throw error;
  }

  return result;
}

// 인증 API
export const authApi = {
  // 로그인
  async login({ email, password }) {
    const data = await apiFetch("/auth/login", {
      method: "POST",
      body: { email, password },
    });

    // 로그인 응답에 Access Token이 있는지 확인한다.
    if (!data?.accessToken) {
      const error = new Error("로그인 응답에 Access Token이 없습니다.");

      error.code = "INVALID_RESPONSE";
      error.status = 200;
      error.fieldErrors = [];

      throw error;
    }

    // Access Token은 메모리에만 저장한다.
    setAccessToken(data.accessToken);

    return data;
  },

  // 회원가입
  async signup({ email, password, nickname, regionId }) {
    return apiFetch("/auth/signup", {
      method: "POST",
      body: { email, password, nickname, regionId },
    });
  },

  // 로그아웃
  async logout() {
    try {
      return await apiFetch("/auth/logout", {
        method: "POST",
      });
    } finally {
      // 로그아웃 요청의 성공 여부와 관계없이 토큰을 제거한다.
      clearAccessToken();
    }
  },
};

// TODO: 다음 스프린트에서 Refresh Token 자동 갱신 구현
