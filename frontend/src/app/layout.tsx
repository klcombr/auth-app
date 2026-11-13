import AuthProvider from './components/AuthContext'
import 'styles/globals.css'

export const metadata = {
  title: 'AuthApp - Sistema de Autenticação',
  description: 'Projeto completo de autenticação com JWT e React',
}

export default function RootLayout({ children }) {
  return (
    <html lang="pt-BR">
      <body>
        <AuthProvider>
          {children}
        </AuthProvider>
      </body>
    </html>
  )
}
