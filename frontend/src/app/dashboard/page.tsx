'use client'

import { useEffect, useState } from 'react'
import axios from 'axios'
import { useRouter } from 'next/navigation'
import styles from '@/styles/Dashboard.module.css'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api'

export default function DashboardPage() {
  const router = useRouter()
  const [user, setUser] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const token = localStorage.getItem('access_token')
    if (!token) {
      router.push('/login')
      return
    }

    const fetchUser = async () => {
      try {
        const res = await axios.get(`${API_URL}/users/me`, {
          headers: { Authorization: `Bearer ${token}` }
        })
        setUser(res.data)
      } catch {
        localStorage.removeItem('access_token')
        localStorage.removeItem('refresh_token')
        router.push('/login')
      } finally {
        setLoading(false)
      }
    }

    fetchUser()
  }, [router])

  const handleLogout = () => {
    const refreshToken = localStorage.getItem('refresh_token')
    const token = localStorage.getItem('access_token')
    
    axios.post(`${API_URL}/auth/logout`, 
      { refresh_token: refreshToken },
      { headers: { Authorization: `Bearer ${token}` } }
    ).catch(() => {})

    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    localStorage.removeItem('user')
    router.push('/login')
  }

  if (loading) return <div className={styles.center}><p>Carregando...</p></div>

  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <h1>Dashboard</h1>
        <button onClick={handleLogout} className={styles.logoutBtn}>Sair</button>
      </header>
      
      <main className={styles.main}>
        <div className={styles.profileCard}>
          <h2>Perfil do Usuário</h2>
          <div className={styles.info}>
            <p><strong>ID:</strong> {user?.id}</p>
            <p><strong>Email:</strong> {user?.email}</p>
            <p><strong>Nome:</strong> {user?.full_name}</p>
            <p><strong>Status:</strong> {user?.is_active ? 'Ativo' : 'Inativo'}</p>
            <p><strong>Membro desde:</strong> {new Date(user?.created_at).toLocaleDateString('pt-BR')}</p>
          </div>
        </div>
        
        <div className={styles.apiSection}>
          <h2>📚 Documentação da API</h2>
          <div className={styles.apiList}>
            <a href="/docs" target="_blank" rel="noopener noreferrer" className={styles.apiLink}>
              Swagger UI - Teste os endpoints
            </a>
            <p className={styles.note}>Acesse http://localhost:8000/docs para testar a API completamenta.</p>
          </div>
        </div>
      </main>
    </div>
  )
}
