import { useEffect, useState } from 'react'

// 남은 시간처럼 시각에 따라 바뀌는 표시를 주기적으로 다시 그리기 위한 현재 시각(ms)
function useNow(intervalMs = 1000) {
  const [now, setNow] = useState(() => Date.now())

  useEffect(() => {
    const timer = setInterval(() => setNow(Date.now()), intervalMs)

    return () => clearInterval(timer)
  }, [intervalMs])

  return now
}

export default useNow
