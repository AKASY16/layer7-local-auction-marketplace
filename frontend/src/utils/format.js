const priceFormatter = new Intl.NumberFormat('ko-KR')

// 85000 → 85,000원
export function formatPrice(amount) {
  return `${priceFormatter.format(amount)}원`
}

const pad = (value) => String(value).padStart(2, '0')

// 1일 이상 "1일 3시간", 1시간 이상 "5시간 20분", 1시간 미만 "12:34"(분:초), 지나면 "마감"
// 초 단위는 올림해서 마감 직전에 "00:00"이 보이지 않게 한다
export function formatRemainingTime(milliseconds) {
  if (milliseconds <= 0) {
    return '마감'
  }

  const totalSeconds = Math.ceil(milliseconds / 1000)
  const days = Math.floor(totalSeconds / 86400)
  const hours = Math.floor((totalSeconds % 86400) / 3600)
  const minutes = Math.floor((totalSeconds % 3600) / 60)
  const seconds = totalSeconds % 60

  if (days > 0) {
    return `${days}일 ${hours}시간`
  }

  if (hours > 0) {
    return `${hours}시간 ${minutes}분`
  }

  return `${pad(minutes)}:${pad(seconds)}`
}

// 상품 상태 등급 이름 (docs/02-requirements.md). 이름을 내려주는 API가 없어 프론트에 둔다
const productConditionLabels = {
  UNOPENED: '미개봉',
  LIKE_NEW: '거의 새것',
  GOOD: '양호',
  FAIR: '사용감 있음',
  DAMAGED: '하자 있음',
  NEEDS_REPAIR: '수리 필요',
}

export function formatProductCondition(condition) {
  return productConditionLabels[condition] ?? condition
}
