export function getApiErrorMessage(error) {
  switch (error?.code) {
    case 'AUTH_INVALID_CREDENTIALS':
      return '이메일 또는 비밀번호를 확인해 주세요.'

    case 'USER_EMAIL_DUPLICATED':
      return '이미 가입된 이메일입니다.'

    default:
      return error?.message || '요청 처리 중 오류가 발생했습니다.'
  }
}
