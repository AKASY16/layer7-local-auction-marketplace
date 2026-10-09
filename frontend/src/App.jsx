import "./App.css";
import { BrowserRouter, Routes, Route } from "react-router-dom";

import Layout from "./components/Layout/Layout.jsx";

import Home from "./pages/Home";
import Login from "./pages/Login";
import Signup from "./pages/Signup";
import AuctionList from "./pages/AuctionList";
import AuctionDetail from "./pages/AuctionDetail";
import ProductRegister from "./pages/ProductRegister";
import MyPage from "./pages/MyPage";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route
          path="/"
          element={
            <Layout
              title="Layer7 Auction"
              footermessage="정상적으로 작동합니다."
            />
          }
        >
          <Route index element={<Home />} />
          <Route path="login" element={<Login />} />
          <Route path="signup" element={<Signup />} />
          <Route path="auctions" element={<AuctionList />} />
          <Route path="auctions/:id" element={<AuctionDetail />} />
          {/*경매 상품이 여러개일 때 명령어를 중복 사용하지 않기위해 id를 변수처럼 사용*/}
          <Route path="products/new" element={<ProductRegister />} />
          {/*고정된 경로*/}
          <Route path="mypage" element={<MyPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
