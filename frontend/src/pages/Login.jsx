import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { Lock, Mail, Sparkles, ArrowRight } from 'lucide-react'

const Login = () => {
  const navigate = useNavigate()
  const { login } = useAuth()

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    // Client-side validation
    if (!email || !password) {
      setError('Email and password are required')
      setLoading(false)
      return
    }

    if (!/\S+@\S+\.\S+/.test(email)) {
      setError('Please enter a valid email address')
      setLoading(false)
      return
    }

    try {
      await login({ email, password })
      navigate('/home')
    } catch (err) {
      setError(err.response?.data?.detail || 'Login failed. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center py-12 px-4 sm:px-6 lg:px-8 relative overflow-hidden" style={{
      background: 'linear-gradient(to bottom right, #F5F3FF, #f8fafc, #EFF6FF)'
    }}>
      {/* Decorative background elements */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-40 -right-40 w-80 h-80 rounded-full mix-blend-multiply filter blur-3xl opacity-30 animate-float" style={{
          backgroundColor: '#DDD6FE'
        }}></div>
        <div className="absolute -bottom-40 -left-40 w-80 h-80 rounded-full mix-blend-multiply filter blur-3xl opacity-30 animate-float" style={{
          backgroundColor: '#BFDBFE',
          animationDelay: '2s'
        }}></div>
        <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 w-80 h-80 rounded-full mix-blend-multiply filter blur-3xl opacity-20 animate-float" style={{
          backgroundColor: '#EDE9FE',
          animationDelay: '4s'
        }}></div>
      </div>

      {/* Login Card */}
      <div className="max-w-md w-full space-y-8 relative z-10">
        {/* Logo/Brand Section */}
        <div className="text-center animate-fade-in">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl mb-4 shadow-lg" style={{
            background: 'linear-gradient(to bottom right, #8B5CF6, #3B82F6)'
          }}>
            <Sparkles className="w-8 h-8 text-white" />
          </div>
          <h2 className="text-4xl font-bold">
            <span style={{
              backgroundImage: 'linear-gradient(to right, #7C3AED, #2563EB)',
              WebkitBackgroundClip: 'text',
              backgroundClip: 'text',
              color: 'transparent'
            }}>Career Intelligence</span>
          </h2>
          <p className="mt-2 text-gray-600">Sign in to your account</p>
        </div>

        {/* Form Card */}
        <div className="rounded-2xl shadow-2xl p-8 animate-slide-up" style={{
          backgroundColor: 'rgba(255, 255, 255, 0.9)',
          backdropFilter: 'blur(12px)',
          border: '1px solid rgba(255, 255, 255, 0.3)',
          boxShadow: '0 8px 32px 0 rgba(31, 38, 135, 0.15)'
        }}>
          <form className="space-y-6" onSubmit={handleSubmit}>
            {error && (
              <div className="rounded-lg p-4 animate-scale-in" data-testid="login-error" style={{
                backgroundColor: '#FEF2F2',
                border: '1px solid #FECACA'
              }}>
                <p className="text-sm" style={{ color: '#991B1B' }}>{error}</p>
              </div>
            )}

            <div className="space-y-5">
              {/* Email Input */}
              <div>
                <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-2">
                  Email address
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                    <Mail className="h-5 w-5 text-gray-400" />
                  </div>
                  <input
                    id="email"
                    name="email"
                    type="email"
                    autoComplete="email"
                    required
                    value={email}
                    onChange={(e) => {
                      setEmail(e.target.value)
                      setError('') // Clear error on input change
                    }}
                    data-testid="login-email"
                    className="block w-full pl-12 pr-4 py-3 border border-gray-300 rounded-lg bg-white text-gray-900 placeholder-gray-400 transition-all duration-200 focus:outline-none"
                    placeholder="you@example.com"
                    onFocus={(e) => {
                      e.target.style.boxShadow = '0 0 0 3px rgba(139, 92, 246, 0.3)'
                      e.target.style.borderColor = '#8B5CF6'
                    }}
                    onBlur={(e) => {
                      e.target.style.boxShadow = 'none'
                      e.target.style.borderColor = '#D1D5DB'
                    }}
                  />
                </div>
              </div>

              {/* Password Input */}
              <div>
                <label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-2">
                  Password
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                    <Lock className="h-5 w-5 text-gray-400" />
                  </div>
                  <input
                    id="password"
                    name="password"
                    type="password"
                    autoComplete="current-password"
                    required
                    value={password}
                    onChange={(e) => {
                      setPassword(e.target.value)
                      setError('') // Clear error on input change
                    }}
                    data-testid="login-password"
                    className="block w-full pl-12 pr-4 py-3 border border-gray-300 rounded-lg bg-white text-gray-900 placeholder-gray-400 transition-all duration-200 focus:outline-none"
                    placeholder="••••••••"
                    onFocus={(e) => {
                      e.target.style.boxShadow = '0 0 0 3px rgba(139, 92, 246, 0.3)'
                      e.target.style.borderColor = '#8B5CF6'
                    }}
                    onBlur={(e) => {
                      e.target.style.boxShadow = 'none'
                      e.target.style.borderColor = '#D1D5DB'
                    }}
                  />
                </div>
              </div>
            </div>

            {/* Submit Button */}
            <div>
              <button
                type="submit"
                disabled={loading}
                data-testid="login-submit"
                className="group relative w-full flex justify-center items-center gap-2 py-3 px-4 border border-transparent text-base font-medium rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200 shadow-lg hover:shadow-xl"
                style={{
                  background: loading ? 'linear-gradient(to right, #8B5CF6, #3B82F6)' : 'linear-gradient(to right, #7C3AED, #2563EB)',
                  boxShadow: '0 10px 15px -3px rgba(139, 92, 246, 0.4)'
                }}
                onMouseEnter={(e) => {
                  if (!loading) {
                    e.target.style.background = 'linear-gradient(to right, #6D28D9, #1D4ED8)'
                  }
                }}
                onMouseLeave={(e) => {
                  if (!loading) {
                    e.target.style.background = 'linear-gradient(to right, #7C3AED, #2563EB)'
                  }
                }}
              >
                {loading ? (
                  <>
                    <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
                    <span>Signing in...</span>
                  </>
                ) : (
                  <>
                    <span>Sign in</span>
                    <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform duration-200" />
                  </>
                )}
              </button>
            </div>

            {/* Register Link */}
            <div className="text-center">
              <Link
                to="/register"
                className="font-medium transition-colors duration-200 inline-flex items-center gap-1"
                style={{ color: '#7C3AED' }}
                onMouseEnter={(e) => e.target.style.color = '#6D28D9'}
                onMouseLeave={(e) => e.target.style.color = '#7C3AED'}
              >
                Don&apos;t have an account?
                <span className="underline">Register now</span>
              </Link>
            </div>
          </form>
        </div>

        {/* Footer Text */}
        <p className="text-center text-sm text-gray-500 animate-fade-in">
          Powered by AI and Graph Technology
        </p>
      </div>
    </div>
  )
}

export default Login
