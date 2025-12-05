import { Link, useLocation, useNavigate } from 'react-router-dom'
import { useState } from 'react'
import { MessageCircle, Upload, LogOut, User, Menu, X, Sparkles, Home as HomeIcon, Activity } from 'lucide-react'

export default function Navigation() {
  const location = useLocation()
  const navigate = useNavigate()
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
  const [userMenuOpen, setUserMenuOpen] = useState(false)

  // Get user email from localStorage or context (simplified for now)
  const userEmail = localStorage.getItem('user_email') || 'user@example.com'

  const handleLogout = () => {
    try {
      // Clear auth token
      localStorage.removeItem('auth_token')

      // Clear any other user data
      localStorage.removeItem('chat_messages')
      localStorage.removeItem('user_email')
    } catch (error) {
      // localStorage might be unavailable in private browsing or quota exceeded
      console.error('Failed to clear localStorage:', error)
      // Continue with logout even if localStorage fails
    }

    // Redirect to login
    navigate('/login')
  }

  const isActive = (path) => location.pathname === path

  const navLinks = [
    { path: '/home', label: 'Home', icon: HomeIcon },
    { path: '/chat', label: 'Chat', icon: MessageCircle },
    { path: '/upload', label: 'Upload', icon: Upload },
    { path: '/monitor', label: 'Monitor', icon: Activity },
  ]

  return (
    <nav className="bg-gradient-to-r from-primary-600 via-primary-500 to-secondary-600 shadow-lg sticky top-0 z-50 backdrop-blur-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          {/* Logo / Brand */}
          <Link 
            to="/home" 
            className="flex items-center gap-2 text-white hover:opacity-90 transition-opacity group"
          >
            <div className="w-10 h-10 bg-white/20 backdrop-blur-sm rounded-lg flex items-center justify-center group-hover:bg-white/30 transition-all duration-200">
              <Sparkles className="w-6 h-6 text-white" />
            </div>
            <div className="hidden sm:block">
              <span className="text-xl font-bold">Career Intelligence</span>
            </div>
          </Link>

          {/* Desktop Navigation Links */}
          <div className="hidden md:flex items-center space-x-1">
            {navLinks.map(({ path, label, icon: Icon }) => (
              <Link
                key={path}
                to={path}
                aria-current={isActive(path) ? 'page' : undefined}
                className={`
                  flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200
                  ${
                    isActive(path)
                      ? 'bg-white/20 text-white shadow-lg backdrop-blur-sm'
                      : 'text-white/90 hover:bg-white/10 hover:text-white'
                  }
                `}
              >
                <Icon className="w-4 h-4" />
                <span>{label}</span>
              </Link>
            ))}
          </div>

          {/* Desktop User Menu */}
          <div className="hidden md:flex items-center gap-4">
            <div className="relative">
              <button
                onClick={() => setUserMenuOpen(!userMenuOpen)}
                className="flex items-center gap-2 px-3 py-2 rounded-lg bg-white/10 hover:bg-white/20 text-white transition-all duration-200 backdrop-blur-sm"
                aria-label="User menu"
                aria-expanded={userMenuOpen}
              >
                <div className="w-8 h-8 bg-white/20 rounded-full flex items-center justify-center">
                  <User className="w-4 h-4" />
                </div>
                <span className="text-sm font-medium max-w-[150px] truncate">
                  {userEmail}
                </span>
              </button>

              {/* User Dropdown Menu */}
              {userMenuOpen && (
                <>
                  <div 
                    className="fixed inset-0 z-10" 
                    onClick={() => setUserMenuOpen(false)}
                  ></div>
                  <div className="absolute right-0 mt-2 w-56 bg-white rounded-lg shadow-xl border border-gray-100 py-2 z-20 animate-scale-in">
                    <div className="px-4 py-3 border-b border-gray-100">
                      <p className="text-sm font-medium text-gray-900">Signed in as</p>
                      <p className="text-sm text-gray-600 truncate">{userEmail}</p>
                    </div>
                    <button
                      onClick={handleLogout}
                      className="w-full flex items-center gap-2 px-4 py-2 text-sm text-error-600 hover:bg-error-50 transition-colors duration-200"
                    >
                      <LogOut className="w-4 h-4" />
                      <span>Logout</span>
                    </button>
                  </div>
                </>
              )}
            </div>
          </div>

          {/* Mobile menu button */}
          <div className="md:hidden flex items-center">
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="p-2 rounded-lg text-white hover:bg-white/10 transition-colors duration-200"
              aria-label="Toggle mobile menu"
              aria-expanded={mobileMenuOpen}
            >
              {mobileMenuOpen ? (
                <X className="w-6 h-6" />
              ) : (
                <Menu className="w-6 h-6" />
              )}
            </button>
          </div>
        </div>

        {/* Mobile Menu */}
        {mobileMenuOpen && (
          <div className="md:hidden py-4 space-y-2 animate-slide-up">
            {navLinks.map(({ path, label, icon: Icon }) => (
              <Link
                key={path}
                to={path}
                onClick={() => setMobileMenuOpen(false)}
                aria-current={isActive(path) ? 'page' : undefined}
                className={`
                  flex items-center gap-3 px-4 py-3 rounded-lg text-sm font-medium transition-all duration-200
                  ${
                    isActive(path)
                      ? 'bg-white/20 text-white shadow-lg'
                      : 'text-white/90 hover:bg-white/10 hover:text-white'
                  }
                `}
              >
                <Icon className="w-5 h-5" />
                <span>{label}</span>
              </Link>
            ))}
            
            {/* Mobile User Info & Logout */}
            <div className="pt-4 border-t border-white/20 space-y-2">
              <div className="px-4 py-2">
                <p className="text-xs text-white/70">Signed in as</p>
                <p className="text-sm text-white font-medium truncate">{userEmail}</p>
              </div>
              <button
                onClick={handleLogout}
                className="w-full flex items-center gap-3 px-4 py-3 rounded-lg text-sm font-medium text-white/90 hover:bg-white/10 hover:text-white transition-all duration-200"
              >
                <LogOut className="w-5 h-5" />
                <span>Logout</span>
              </button>
            </div>
          </div>
        )}
      </div>
    </nav>
  )
}
