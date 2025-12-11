import PropTypes from 'prop-types'
import Navigation from './Navigation'

export default function Layout({ children }) {
  return (
    <div className="flex flex-col min-h-screen relative overflow-hidden bg-slate-900">
      {/* Background gradients */}
      <div className="fixed inset-0 pointer-events-none">
        <div className="absolute top-0 left-1/4 w-96 h-96 bg-primary-500/20 rounded-full blur-3xl" />
        <div className="absolute bottom-0 right-1/4 w-96 h-96 bg-secondary-500/20 rounded-full blur-3xl" />
      </div>

      <Navigation />
      
      <main className="flex-1 relative container mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {children}
      </main>
    </div>
  )
}

Layout.propTypes = {
  children: PropTypes.node.isRequired
}
