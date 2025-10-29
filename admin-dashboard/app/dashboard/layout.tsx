import Link from 'next/link'
import { Home, Users, RefreshCw, CheckCircle, School, Download, Settings } from 'lucide-react'

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <div className="min-h-screen bg-gray-50">
      {/* Top Navigation */}
      <nav className="bg-white shadow-sm border-b">
        <div className="container mx-auto px-4">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center space-x-8">
              <Link href="/" className="text-xl font-bold text-blue-600">
                VESPA Admin
              </Link>
              <div className="hidden md:flex space-x-4">
                <NavLink href="/dashboard" icon={<Home className="w-4 h-4" />}>
                  Home
                </NavLink>
                <NavLink href="/dashboard/students" icon={<Users className="w-4 h-4" />}>
                  Students
                </NavLink>
                <NavLink href="/dashboard/sync" icon={<RefreshCw className="w-4 h-4" />}>
                  Sync
                </NavLink>
                <NavLink href="/dashboard/quality" icon={<CheckCircle className="w-4 h-4" />}>
                  Quality
                </NavLink>
                <NavLink href="/dashboard/schools" icon={<School className="w-4 h-4" />}>
                  Schools
                </NavLink>
                <NavLink href="/dashboard/export" icon={<Download className="w-4 h-4" />}>
                  Export
                </NavLink>
                <NavLink href="/dashboard/bulk" icon={<Settings className="w-4 h-4" />}>
                  Bulk Ops
                </NavLink>
              </div>
            </div>
            <div className="text-sm text-gray-600">
              tony@vespa.academy
            </div>
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <main className="container mx-auto px-4 py-8">
        {children}
      </main>

      {/* Footer */}
      <footer className="bg-white border-t mt-12">
        <div className="container mx-auto px-4 py-6 text-center text-sm text-gray-600">
          <p>VESPA Admin Dashboard v1.0 | Database: Supabase</p>
          <p className="mt-1">Last sync check available in Sync Monitor</p>
        </div>
      </footer>
    </div>
  )
}

function NavLink({ href, icon, children }: { 
  href: string
  icon: React.ReactNode
  children: React.ReactNode 
}) {
  return (
    <Link
      href={href}
      className="flex items-center space-x-2 px-3 py-2 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-100 hover:text-blue-600 transition-colors"
    >
      {icon}
      <span>{children}</span>
    </Link>
  )
}

