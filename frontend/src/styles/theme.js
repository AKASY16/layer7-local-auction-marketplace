// 목업에서 뽑은 디자인 값 (#52). 화면과 컴포넌트는 색·크기를 직접 적지 않고 여기 값을 가져다 쓴다
const theme = {
  colors: {
    primary: '#7A1E28', // 와인: 주요 버튼, 선택된 칩, 가격, 로고, 경고·오류 문구
    onPrimary: '#FFFFFF', // 와인색 배경 위 글자
    primaryDark: '#4B0E14', // 섹션 제목
    primaryTint: '#F6ECEC', // 선택·강조 배경, 입력칸 포커스 테두리 바깥
    gold: '#A57C45', // 배지, 장식 아이콘
    // 남은 시간 전용. 흰 배경에서 명암비가 4.4:1이라 작은 글씨의 오류 문구에는 쓰지 않는다
    danger: '#E0353D',
    success: '#3A8A4C', // 완료·확인 체크
    successTint: '#E6EEE2', // 추천·확인 박스 배경
    cream: '#FAF6F1', // 안내 박스 배경
    beige: '#C8B497', // 검색창 테두리
    text: '#1E1E1E', // 제목, 본문
    // 설명, 라벨. 목업 값(#8E8C8C)은 흰 배경에서 명암비가 3.3:1이라, 작은 글씨 기준(4.5:1)을 넘도록 조금 진하게 했다
    textSub: '#737171',
    textMuted: '#A8A8A8', // 입력칸 안내문
    border: '#E4E4E4', // 입력칸, 구분선
    disabled: '#F4F4F5', // 비활성 입력칸 배경
    background: '#FFFFFF',
  },

  fonts: {
    body: "'Pretendard Variable', Pretendard, -apple-system, BlinkMacSystemFont, system-ui, 'Apple SD Gothic Neo', 'Malgun Gothic', sans-serif",
  },

  // 휴대폰 폭 375px 기준
  fontSizes: {
    title: '20px', // 섹션 제목
    cardTitle: '16px',
    body: '15px',
    bodySmall: '14px',
    sub: '13px',
    label: '12px',
    priceList: '18px',
    priceDetail: '28px',
  },

  fontWeights: {
    regular: 400,
    medium: 500,
    semibold: 600,
    bold: 700,
  },

  space: {
    xs: '4px',
    sm: '8px',
    md: '12px',
    lg: '16px',
    xl: '24px',
  },

  radius: {
    control: '10px', // 입력칸, 버튼, 카드 사진
    box: '12px', // 큰 박스
    pill: '999px', // 칩, 배지
  },

  layout: {
    maxWidth: '480px', // PC에서는 가운데 이 폭으로 보인다
    gutter: '16px', // 화면 좌우 여백
    headerHeight: '56px',
  },
}

export default theme
