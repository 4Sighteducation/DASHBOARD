'use client'

import Link from 'next/link'
import { useState } from 'react'
import { Home, Users, RefreshCw, CheckCircle, School, Download, Settings, Menu, X } from 'lucide-react'

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)

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
              {/* Desktop Menu */}
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
            
            {/* Desktop: Email */}
            <div className="hidden md:block text-sm text-gray-600">
              tony@vespa.academy
            </div>
            
            {/* Mobile: Hamburger */}
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="md:hidden p-2 rounded-lg hover:bg-gray-100"
            >
              {mobileMenuOpen ? (
                <X className="w-6 h-6 text-gray-600" />
              ) : (
                <Menu className="w-6 h-6 text-gray-600" />
              )}
            </button>
          </div>
          
          {/* Mobile Menu */}
          {mobileMenuOpen && (
            <div className="md:hidden border-t py-4">
              <div className="flex flex-col space-y-2">
                <MobileNavLink href="/dashboard" icon={<Home className="w-4 h-4" />} onClick={() => setMobileMenuOpen(false)}>
                  Home
                </MobileNavLink>
                <MobileNavLink href="/dashboard/students" icon={<Users className="w-4 h-4" />} onClick={() => setMobileMenuOpen(false)}>
                  Students
                </MobileNavLink>
                <MobileNavLink href="/dashboard/sync" icon={<RefreshCw className="w-4 h-4" />} onClick={() => setMobileMenuOpen(false)}>
                  Sync
                </MobileNavLink>
                <MobileNavLink href="/dashboard/quality" icon={<CheckCircle className="w-4 h-4" />} onClick={() => setMobileMenuOpen(false)}>
                  Quality
                </MobileNavLink>
                <MobileNavLink href="/dashboard/schools" icon={<School className="w-4 h-4" />} onClick={() => setMobileMenuOpen(false)}>
                  Schools
                </MobileNavLink>
                <MobileNavLink href="/dashboard/export" icon={<Download className="w-4 h-4" />} onClick={() => setMobileMenuOpen(false)}>
                  Export
                </MobileNavLink>
                <MobileNavLink href="/dashboard/bulk" icon={<Settings className="w-4 h-4" />} onClick={() => setMobileMenuOpen(false)}>
                  Bulk Ops
                </MobileNavLink>
              </div>
              <div className="mt-4 pt-4 border-t text-sm text-gray-600">
                tony@vespa.academy
              </div>
            </div>
          )}
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

function MobileNavLink({ href, icon, children, onClick }: { 
  href: string
  icon: React.ReactNode
  children: React.ReactNode
  onClick: () => void
}) {
  return (
    <Link
      href={href}
      onClick={onClick}
      className="flex items-center space-x-3 px-4 py-3 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-100 hover:text-blue-600 transition-colors"
    >
      {icon}
      <span>{children}</span>
    </Link>
  )
}

