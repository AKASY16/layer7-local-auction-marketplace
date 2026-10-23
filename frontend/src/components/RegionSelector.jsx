import { useEffect, useMemo, useState } from 'react'
import { apiFetch } from '../api/client'
import { getApiErrorMessage } from '../api/errorMessage'
import {
  AuthField,
  AuthLabel,
  RegionSelect,
  RegionMessage,
  RegionError,
  RetryButton,
} from './AuthFormStyles'

// 시도명과 시군구명이 같을 경우 중복 표시 방지
function formatRegionName(region) {
  return region.sidoName === region.sigunguName
    ? region.sidoName
    : `${region.sidoName} ${region.sigunguName}`
}

// 전체 지역 데이터 조회
async function fetchAllRegions(signal) {
  const regions = []
  let page = 0

  while (true) {
    const response = await apiFetch(`/regions?page=${page}&size=50`, {
      signal,
    })

    if (
      !response ||
      !Array.isArray(response.content) ||
      !Number.isInteger(response.totalPages) ||
      response.totalPages < 0
    ) {
      throw new Error('지역 데이터 형식이 올바르지 않습니다.')
    }

    regions.push(...response.content)
    page += 1

    if (page >= response.totalPages) {
      break
    }
  }

  return regions
}

function RegionSelector({ value, onChange, disabled = false }) {
  const [regions, setRegions] = useState([])
  const [selectedSido, setSelectedSido] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [retryCount, setRetryCount] = useState(0)

  useEffect(() => {
    const controller = new AbortController()
    let active = true

    async function loadRegions() {
      setLoading(true)
      setError('')

      try {
        const data = await fetchAllRegions(controller.signal)

        if (!active) return

        setRegions(data)
      } catch (error) {
        if (!active) return

        setRegions([])
        setError(getApiErrorMessage(error))
      } finally {
        if (active) {
          setLoading(false)
        }
      }
    }

    loadRegions()

    return () => {
      active = false
      controller.abort()
    }
  }, [retryCount])

  const sidoList = useMemo(() => {
    return [...new Set(regions.map((region) => region.sidoName))]
  }, [regions])

  const sigunguList = useMemo(() => {
    return regions.filter((region) => region.sidoName === selectedSido)
  }, [regions, selectedSido])

  const selectedRegion = regions.find(
    (region) => String(region.id) === String(value),
  )

  function handleSidoChange(event) {
    setSelectedSido(event.target.value)
    onChange('')
  }

  function handleSigunguChange(event) {
    onChange(event.target.value)
  }

  return (
    <>
      <AuthField>
        <AuthLabel htmlFor="sido">시도</AuthLabel>

        <RegionSelect
          id="sido"
          value={selectedSido}
          onChange={handleSidoChange}
          disabled={disabled || loading || Boolean(error)}
          required
        >
          <option value="">
            {loading ? '지역 불러오는 중...' : '시도를 선택하세요'}
          </option>

          {sidoList.map((sido) => (
            <option key={sido} value={sido}>
              {sido}
            </option>
          ))}
        </RegionSelect>
      </AuthField>

      <AuthField>
        <AuthLabel htmlFor="regionId">시군구</AuthLabel>

        <RegionSelect
          id="regionId"
          name="regionId"
          value={value}
          onChange={handleSigunguChange}
          disabled={disabled || loading || Boolean(error) || !selectedSido}
          required
        >
          <option value="">시군구를 선택하세요</option>

          {sigunguList.map((region) => (
            <option key={region.id} value={region.id}>
              {region.sigunguName}
            </option>
          ))}
        </RegionSelect>
      </AuthField>

      {selectedRegion && (
        <RegionMessage aria-live="polite">
          선택한 지역: {formatRegionName(selectedRegion)}
        </RegionMessage>
      )}

      {error && (
        <>
          <RegionError role="alert">지역을 불러오지 못했습니다.</RegionError>

          <RetryButton
            type="button"
            onClick={() => setRetryCount((count) => count + 1)}
            disabled={disabled}
          >
            다시 불러오기
          </RetryButton>
        </>
      )}

      {!loading && !error && regions.length === 0 && (
        <RegionMessage>선택할 수 있는 지역이 없습니다.</RegionMessage>
      )}
    </>
  )
}

export default RegionSelector
