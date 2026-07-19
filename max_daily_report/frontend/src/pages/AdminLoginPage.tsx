import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

export function AdminLoginPage() {
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const navigate = useNavigate()

  const submit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!password) {
      setError('Введите пароль')
      return
    }
    window.localStorage.setItem('admin_password', password)
    setError('')
    navigate('/admin/catalogs')
  }

  return (
    <div style={{ maxWidth: 360, margin: '80px auto', padding: 24, fontFamily: 'system-ui' }}>
      <h2>Вход в админку</h2>
      <p style={{ color: '#666', fontSize: 14 }}>
        Введите пароль администратора (задаётся в .env ADMIN_PASSWORD на сервере).
      </p>
      <form onSubmit={submit}>
        <input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="Пароль"
          style={{ width: '100%', padding: 10, fontSize: 16, marginBottom: 12 }}
          autoFocus
        />
        {error && <p style={{ color: 'red', fontSize: 13 }}>{error}</p>}
        <button type="submit" style={{ width: '100%', padding: 10, fontSize: 16 }}>
          Войти
        </button>
      </form>
    </div>
  )
}
