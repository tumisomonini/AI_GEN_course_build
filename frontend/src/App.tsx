import { useState } from 'react'
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom'
import { Button } from './components/ui/button'
import { Home } from './pages/Home'
import './index.css'

function App() {
  return (
    <Router>
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
        <nav className="bg-white/80 backdrop-blur-md border-b border-gray-200 p-4">
          <div className="max-w-6xl mx-auto flex justify-between items-center">
            <Link to="/" className="text-2xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
              AI Course Gen
            </Link>
            <div className="space-x-4">
              <Link to="/" className="text-gray-600 hover:text-blue-600">Create</Link>
              <Link to="/review" className="text-gray-600 hover:text-blue-600">Review</Link>
            </div>
          </div>
        </nav>
        <main className="max-w-4xl mx-auto p-8">
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/review/:id" element={<div>Review Page (TBD)</div>} />
          </Routes>
        </main>
      </div>
    </Router>
  )
}

export default App

