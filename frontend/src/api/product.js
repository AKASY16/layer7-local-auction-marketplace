import { apiFetch } from './client'

// 1. 이미지 업로드용 URL 발급
export async function requestProductImageUpload(file, signal) {
  const response = await apiFetch('/uploads/product-images', {
    method: 'POST',
    body: {
      files: [
        {
          contentType: file.type,
          size: file.size,
        },
      ],
    },
    signal,
  })

  const upload = response?.uploads?.[0]

  if (
    response?.uploads?.length !== 1 ||
    typeof upload?.objectKey !== 'string' ||
    typeof upload?.uploadUrl !== 'string' ||
    typeof upload?.headers?.['Content-Type'] !== 'string'
  ) {
    throw new Error('업로드 URL 응답 형식이 올바르지 않습니다.')
  }

  if (upload.headers['Content-Type'] !== file.type) {
    throw new Error('서버가 요청한 이미지 형식과 다른 형식을 반환했습니다.')
  }

  return upload
}

// 2. 이미지 파일을 Object Storage에 직접 업로드
export function putProductImage(file, upload, onProgress, signal) {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest()

    const abort = () => xhr.abort()

    const cleanup = () => {
      signal?.removeEventListener('abort', abort)
    }

    if (signal?.aborted) {
      reject(new DOMException('업로드가 취소되었습니다.', 'AbortError'))
      return
    }

    xhr.open('PUT', upload.uploadUrl)

    // 이미지 저장소 요청에는 JWT나 사용자 쿠키를 보내지 않음
    xhr.withCredentials = false

    Object.entries(upload.headers).forEach(([name, value]) => {
      xhr.setRequestHeader(name, value)
    })

    // 업로드 진행률
    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable) {
        const progress = Math.min(
          100,
          Math.round((event.loaded / event.total) * 100),
        )

        onProgress(progress)
      }
    }

    xhr.onload = () => {
      cleanup()

      if (xhr.status >= 200 && xhr.status < 300) {
        resolve(upload.objectKey)
      } else {
        reject(
          new Error(
            `이미지 저장 실패 (HTTP ${xhr.status}). 다시 시도해 주세요.`,
          ),
        )
      }
    }

    xhr.onerror = () => {
      cleanup()

      reject(
        new Error(
          '이미지 저장소에 연결하지 못했습니다. 네트워크 및 CORS 설정을 확인해 주세요.',
        ),
      )
    }

    xhr.onabort = () => {
      cleanup()
      reject(new DOMException('업로드가 취소되었습니다.', 'AbortError'))
    }

    signal?.addEventListener('abort', abort, { once: true })

    xhr.send(file)
  })
}

// 3. 상품 관련 API
export const productApi = {
  create(data, signal) {
    return apiFetch('/products', {
      method: 'POST',
      body: data,
      signal,
    })
  },

  get(id, signal) {
    return apiFetch(`/products/${encodeURIComponent(id)}`, {
      signal,
    })
  },
}
