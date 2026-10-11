const API_BASE_URL = "/api/v1"; // API 요청 시 사용하는 기본 경로 apifetch("/auth/login"); -> /api/v1/auth/login

// Access Token은 메모리에만 보관한다.
let accessToken = null; // 페이지 새로 고침 시 초기화

export function setAccessToken(token) {
  accessToken = typeof token === "string" && token ? token : null;
} // 토큰이 문자열이고 비어있지 않으면 accessToken에 저장, 아니면 null로 초기화

export function getAccessToken() {
  return accessToken;
}

export function clearAccessToken() {
  accessToken = null;
} // 로그아웃 or 인증 정보 초기화 시 사용

export async function apiFetch(path, options = {}) {
  if (typeof path !== "string" || !path.startsWith("/")) {
    throw new Error("API 경로는 /로 시작해야 합니다.");
  }

  const headers = new Headers(options.headers || {});
  const isFormData =
    typeof FormData !== "undefined" && options.body instanceof FormData;

  if (options.body != null && !isFormData && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  if (accessToken) {
    headers.set("Authorization", `Bearer ${accessToken}`);
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers,
    credentials: "include",
  });

  if (response.status === 204) {
    return null;
  }

  const contentType = response.headers.get("content-type") || "";
  const result = contentType.includes("application/json")
    ? await response.json()
    : await response.text();

  if (!response.ok) {
    const body =
      result && typeof result === "object" && result !== null ? result : {};

    const error = new Error(
      body.message || "요청 처리 중 오류가 발생했습니다.",
    );

    error.status = response.status;
    error.code = body.code || "UNKNOWN_ERROR";
    error.fieldErrors = Array.isArray(body.fieldErrors) ? body.fieldErrors : [];

    throw error;
  }

  return result;
}
