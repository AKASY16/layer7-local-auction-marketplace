import styled from "styled-components";

const Title = styled.h1`
  color: ${({ theme }) => theme.colors.primary};
  font-family: ${({ theme }) => theme.fonts.main};
  margin-bottom: ${({ theme }) => theme.spacing.large};
`;

function Home() {
  return (
    <div>
      <Title>Layer7 홈 화면</Title>
      <p>안녕하세요.</p>
    </div>
  );
}

export default Home;
