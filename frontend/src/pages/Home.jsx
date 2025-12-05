import { useNavigate } from 'react-router-dom'
import { useState, useEffect } from 'react'
import { MessageCircle, Upload, Sparkles, Database, TrendingUp } from 'lucide-react'
import Navigation from '../components/Layout/Navigation'
import api from '../services/api'

const Home = () => {
  const navigate = useNavigate()

  // Fetch real stats from API
  const [stats, setStats] = useState({
    jobs: '0',
    skills: '0',
    companies: '0',
    lastUpdated: 'Loading...'
  })
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const response = await api.get('/stats')
        setStats({
          jobs: response.data.jobs.toLocaleString(),
          skills: response.data.skills.toLocaleString(),
          companies: response.data.companies.toLocaleString(),
          lastUpdated: response.data.lastUpdated
        })
      } catch (error) {
        console.error('Failed to fetch stats:', error)
        // Keep default values on error
        setStats({
          jobs: 'N/A',
          skills: 'N/A',
          companies: 'N/A',
          lastUpdated: 'unavailable'
        })
      } finally {
        setLoading(false)
      }
    }

    fetchStats()
  }, [])

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-purple-50/30 to-blue-50/30">
      {/* Navigation */}
      <Navigation />

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        {/* Hero Section */}
        <div className="text-center mb-16 animate-fade-in">
          <div className="inline-flex items-center gap-2 px-4 py-2 bg-primary-100 rounded-full text-primary-700 font-medium mb-6 animate-scale-in">
            <Sparkles className="w-4 h-4" />
            <span>Career Intelligence Platform</span>
          </div>
          
          <h1 className="text-5xl md:text-6xl font-bold text-gray-900 mb-6">
            Discover Your <span className="gradient-text">Career Path</span>
          </h1>
          
          <p className="text-xl text-gray-600 max-w-2xl mx-auto mb-8">
            Explore skills, jobs, and career opportunities powered by advanced graph technology and AI.
          </p>
        </div>

        {/* Action Cards */}
        <div className="grid md:grid-cols-2 gap-8 mb-16 max-w-5xl mx-auto">
          {/* Chat Card */}
          <button
            onClick={() => navigate('/chat')}
            className="group relative overflow-hidden rounded-2xl bg-gradient-to-br from-primary-500 to-primary-700 p-1 transition-all duration-300 hover:shadow-2xl hover:shadow-primary-500/50 hover:scale-105 animate-slide-up"
            style={{ animationDelay: '0.1s' }}
          >
            <div className="relative h-full bg-white rounded-xl p-8 transition-all duration-300 group-hover:bg-transparent">
              <div className="absolute inset-0 bg-gradient-to-br from-primary-500 to-primary-700 opacity-0 group-hover:opacity-100 transition-opacity duration-300 rounded-xl" />
              
              <div className="relative z-10">
                <div className="w-16 h-16 bg-primary-100 rounded-2xl flex items-center justify-center mb-6 group-hover:bg-white/20 transition-colors duration-300">
                  <MessageCircle className="w-8 h-8 text-primary-600 group-hover:text-white transition-colors duration-300" />
                </div>
                
                <h3 className="text-2xl font-bold text-gray-900 group-hover:text-white mb-3 transition-colors duration-300">
                  Start Chatting
                </h3>
                
                <p className="text-gray-600 group-hover:text-white/90 mb-6 transition-colors duration-300">
                  Ask questions about careers, skills, and jobs. Get intelligent answers powered by our knowledge graph.
                </p>
                
                <div className="flex items-center text-primary-600 group-hover:text-white font-medium transition-colors duration-300">
                  <span>Ask a question</span>
                  <svg className="w-5 h-5 ml-2 group-hover:translate-x-2 transition-transform duration-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                  </svg>
                </div>
              </div>
            </div>
          </button>

          {/* Upload Card */}
          <button
            onClick={() => navigate('/upload')}
            className="group relative overflow-hidden rounded-2xl bg-gradient-to-br from-secondary-500 to-secondary-700 p-1 transition-all duration-300 hover:shadow-2xl hover:shadow-secondary-500/50 hover:scale-105 animate-slide-up"
            style={{ animationDelay: '0.2s' }}
          >
            <div className="relative h-full bg-white rounded-xl p-8 transition-all duration-300 group-hover:bg-transparent">
              <div className="absolute inset-0 bg-gradient-to-br from-secondary-500 to-secondary-700 opacity-0 group-hover:opacity-100 transition-opacity duration-300 rounded-xl" />
              
              <div className="relative z-10">
                <div className="w-16 h-16 bg-secondary-100 rounded-2xl flex items-center justify-center mb-6 group-hover:bg-white/20 transition-colors duration-300">
                  <Upload className="w-8 h-8 text-secondary-600 group-hover:text-white transition-colors duration-300" />
                </div>
                
                <h3 className="text-2xl font-bold text-gray-900 group-hover:text-white mb-3 transition-colors duration-300">
                  Upload Data
                </h3>
                
                <p className="text-gray-600 group-hover:text-white/90 mb-6 transition-colors duration-300">
                  Upload Skills or Jobs CSV files to enrich the knowledge graph and improve insights.
                </p>
                
                <div className="flex items-center text-secondary-600 group-hover:text-white font-medium transition-colors duration-300">
                  <span>Upload CSV file</span>
                  <svg className="w-5 h-5 ml-2 group-hover:translate-x-2 transition-transform duration-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                  </svg>
                </div>
              </div>
            </div>
          </button>
        </div>

        {/* Stats Section */}
        <div className="max-w-5xl mx-auto">
          <div className="glass rounded-2xl p-8 animate-slide-up" style={{ animationDelay: '0.3s' }}>
            <div className="flex items-center justify-center gap-2 mb-6">
              <Database className="w-5 h-5 text-primary-600" />
              <h3 className="text-lg font-semibold text-gray-900">Knowledge Graph Stats</h3>
            </div>
            
            <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
              <div className="text-center">
                <div className="flex items-center justify-center gap-2 mb-2">
                  <TrendingUp className="w-5 h-5 text-secondary-600" />
                  <p className="text-3xl font-bold text-gray-900">{stats.jobs}</p>
                </div>
                <p className="text-sm text-gray-600">Jobs</p>
              </div>
              
              <div className="text-center">
                <div className="flex items-center justify-center gap-2 mb-2">
                  <Sparkles className="w-5 h-5 text-primary-600" />
                  <p className="text-3xl font-bold text-gray-900">{stats.skills}</p>
                </div>
                <p className="text-sm text-gray-600">Skills</p>
              </div>
              
              <div className="text-center">
                <div className="flex items-center justify-center gap-2 mb-2">
                  <Database className="w-5 h-5 text-secondary-600" />
                  <p className="text-3xl font-bold text-gray-900">{stats.companies}</p>
                </div>
                <p className="text-sm text-gray-600">Companies</p>
              </div>
              
              <div className="text-center">
                <div className="flex items-center justify-center gap-2 mb-2">
                  <MessageCircle className="w-5 h-5 text-primary-600" />
                  <p className="text-sm font-medium text-gray-900">Last Updated</p>
                </div>
                <p className="text-sm text-gray-600">{stats.lastUpdated}</p>
              </div>
            </div>
          </div>
        </div>

        {/* Features Grid (Optional) */}
        <div className="mt-16 max-w-5xl mx-auto">
          <div className="grid md:grid-cols-3 gap-6">
            <div className="card p-6 hover:shadow-lg transition-shadow duration-300 animate-slide-up" style={{ animationDelay: '0.4s' }}>
              <div className="w-12 h-12 bg-primary-100 rounded-lg flex items-center justify-center mb-4">
                <Sparkles className="w-6 h-6 text-primary-600" />
              </div>
              <h4 className="text-lg font-semibold text-gray-900 mb-2">AI-Powered Insights</h4>
              <p className="text-gray-600 text-sm">Get intelligent career recommendations powered by advanced AI and graph technology.</p>
            </div>
            
            <div className="card p-6 hover:shadow-lg transition-shadow duration-300 animate-slide-up" style={{ animationDelay: '0.5s' }}>
              <div className="w-12 h-12 bg-secondary-100 rounded-lg flex items-center justify-center mb-4">
                <Database className="w-6 h-6 text-secondary-600" />
              </div>
              <h4 className="text-lg font-semibold text-gray-900 mb-2">Knowledge Graph</h4>
              <p className="text-gray-600 text-sm">Explore rich connections between skills, jobs, and companies in our comprehensive database.</p>
            </div>
            
            <div className="card p-6 hover:shadow-lg transition-shadow duration-300 animate-slide-up" style={{ animationDelay: '0.6s' }}>
              <div className="w-12 h-12 bg-primary-100 rounded-lg flex items-center justify-center mb-4">
                <TrendingUp className="w-6 h-6 text-primary-600" />
              </div>
              <h4 className="text-lg font-semibold text-gray-900 mb-2">Career Growth</h4>
              <p className="text-gray-600 text-sm">Discover skill gaps and career paths to accelerate your professional development.</p>
            </div>
          </div>
        </div>
      </main>
    </div>
  )
}

export default Home
