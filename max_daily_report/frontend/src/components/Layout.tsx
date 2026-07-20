import { Link, Outlet } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import { Loading } from './Loading.tsx'

export function Layout() {
  const { user, loading, error } = useAuth()

  if (loading) {
    return <Loading />
  }
  if (error || !user) {
    return (
      <div className="screen state-error" role="alert" style={{ maxWidth: 400, margin: '60px auto', padding: 24, textAlign: 'center' }}>
        <p>{error ?? 'Пользователь не авторизован'}</p>
        <p style={{ marginTop: 12 }}>
          <a href="/admin/login" style={{ color: '#2563eb' }}>
            Войти как администратор
          </a>
        </p>
        <p style={{ fontSize: 13, color: '#666', marginTop: 8 }}>
          Откройте приложение через MAX-бот, чтобы заполнять отчёты.
        </p>
      </div>
    )
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
