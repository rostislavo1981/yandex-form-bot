import { Link, Outlet } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import { Loading } from './Loading.tsx'
import { ErrorState } from './ErrorState.tsx'

export function Layout() {
  const { user, loading, error } = useAuth()

  if (loading) {
    return <Loading />
  }
  if (error) {
    return <ErrorState message={error} />
  }
  if (!user) {
    return <ErrorState message="Пользователь не авторизован" />
  }

  const isManager = user.role === 'manager' || user.role === 'admin'

  return (
    <div className="app">
      <header className="app-header">
        <span className="app-title">Ежедневный отчёт</span>
        <span className="app-user">{user.full_name}</span>
      </header>
      <nav className="app-nav">
        <Link to="/report">Заполнить</Link>
        <Link to="/reports">Мои отчёты</Link>
        <Link to="/timesheet">Табель</Link>
        {isManager && <Link to="/status">Статус</Link>}
        {isManager && <Link to="/admin/catalogs">Справочники</Link>}
        {!user && <Link to="/admin/login">Вход админа</Link>}
      </nav>
      <main className="app-main">
        <Outlet />
      </main>
    </div>
  )
}
