import Header from './Header'
import Footer from './Footer'

import { Outlet } from 'react-router'

function Layout({ title, footermessage }) {
  return (
    <div>
      <Header title={title} />

      <Outlet />

      <Footer message={footermessage} />
    </div>
  )
}

export default Layout
