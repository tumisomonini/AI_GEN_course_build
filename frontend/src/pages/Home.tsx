import { useState } from 'react'
import { Button } from '../components/ui/button'
import { Input } from '../components/ui/input'
import { Loader2, Play } from 'lucide-react'

export function Home() {
  const [courseTitle, setCourseTitle] = useState('')
  const [level, setLevel] = useState('beginner')
  const [loading, setLoading] = useState(false)
  const [logs, setLogs] = useState<string[]>([])

  const generateCourse = async () => {
    setLoading(true)
    setLogs([])
    try {
      const res = await fetch('/api/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: courseTitle, level }),
      })
      if (!res.ok) throw new Error('Generation failed')
      const data = await res.json()
      // Redirect to /review/data.course_id
      window.location.href = `/review/${data.course_id}`
    } catch (error) {
      setLogs(prev => [...prev, `Error: ${error}`])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-8">
      <div className="text-center">
        <h1 className="text-5xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent mb-4">
          Generate AI Courses
        </h1>
        <p className="text-xl text-gray-600 max-w-2xl mx-auto">
          Enter course title and level to generate complete curriculum with chapters, topics, and resources.
        </p>
      </div>
      
      <div className="bg-white/70 backdrop-blur-md rounded-2xl p-8 shadow-xl border">
        <div className="space-y-6">
          <div>
            <label className="block text-sm font-medium mb-2">Course Title</label>
            <Input 
              value={courseTitle}
              onChange={(e) => setCourseTitle(e.target.value)}
              placeholder="e.g. Machine Learning for Beginners"
              className="text-2xl py-6 border-2 border-gray-200 focus:border-blue-500"
            />
          </div>
          <div className="flex space-x-4">
            <label className="block text-sm font-medium mb-2 flex-1">
              Level
              <select value={level} onChange={(e) => setLevel(e.target.value)} className="mt-1 block w-full rounded-md border border-gray-300 py-3 px-4 shadow-sm focus:border-blue-500 focus:ring-blue-500">
                <option value="beginner">Beginner</option>
                <option value="intermediate">Intermediate</option>
                <option value="advanced">Advanced</option>
              </select>
            </label>
          </div>
          <Button 
            onClick={generateCourse} 
            disabled={!courseTitle || loading}
            className="w-full h-16 text-xl bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700"
          >
            {loading ? (
              <>
                <Loader2 className="mr-2 h-6 w-6 animate-spin" />
                Generating...
              </>
            ) : (
              <>
                <Play className="mr-2 h-6 w-6" />
                Generate Course
              </>
            )}
          </Button>
        </div>
      </div>

      {logs.length > 0 && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-6">
          <h3 className="font-semibold text-red-800 mb-2">Live Logs</h3>
          <pre className="text-sm text-red-700 whitespace-pre-wrap max-h-48 overflow-y-auto">{logs.join('\n')}</pre>
        </div>
      )}
    </div>
  )
}

