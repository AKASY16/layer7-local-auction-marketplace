export function getApiErrorMessage(error) {
  switch (error?.code) {
    case "INVALID_CREDENTIALS":
      return "이메일 또는 비밀번호를 확인해 주세요.";

    case "DUPLICATE_EMAIL":
      return "이미 가입된 이메일입니다.";

    case "DUPLICATE_NICKNAME":
      return "이미 사용 중인 닉네임입니다.";

    case "VALIDATION_ERROR":
      return "입력한 정보를 확인해 주세요.";

    case "UNAUTHORIZED":
    case "INVALID_TOKEN":
    case "INVALID_REFRESH_TOKEN":
      return "로그인이 만료되었습니다. 다시 로그인해 주세요.";

    case "ACCOUNT_WITHDRAWN":
      return "탈퇴 처리된 계정입니다.";

    case "NETWORK_ERROR":
      return "서버에 연결할 수 없습니다. 네트워크를 확인해 주세요.";

    default:
      return error?.message || "요청 처리 중 오류가 발생했습니다.";
  }
}
