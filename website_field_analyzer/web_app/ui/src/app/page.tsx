'use client'

import React, { useState, useEffect } from 'react'
import { RotateCcw, Play, MousePointer, Type, Clock, ArrowDown, FileText, Code, Save, Terminal, Search } from 'lucide-react'

export default function TrainerPage() {
  const [url, setUrl] = useState('https://sosnc.gov/online_services/search/by_title/search_Business_Registration')
  const [logs, setLogs] = useState<string[]>([])
  const [isConnected, setIsConnected] = useState(false)
  const [commandOutput, setCommandOutput] = useState('')

  // Command Inputs - Decoupled State
  const [clickSelector, setClickSelector] = useState('')
  const [typeSelector, setTypeSelector] = useState('')
  const [typeValue, setTypeValue] = useState('')
  const [pressKey, setPressKey] = useState('')
  const [waitSecs, setWaitSecs] = useState('2')
  const [podSelector, setPodSelector] = useState('button')
  const [podAttr, setPodAttr] = useState('Date formed')
  const [podVal, setPodVal] = useState('1/1/2001')

  const API_URL = 'http://localhost:8000'

  const addLog = (msg: string) => {
    setLogs(prev => [`[${new Date().toLocaleTimeString()}] ${msg}`, ...prev])
  }

  const checkConnection = async () => {
    try {
      // Just check if we can reach it. Using run_generator or just a command might be too heavy.
      // We'll just assume start works.
      setIsConnected(true)
    } catch (e) {
      setIsConnected(false)
    }
  }

  const startTrainer = async () => {
    addLog(`Starting trainer with URL: ${url}...`)
    try {
      const res = await fetch(`${API_URL}/trainer/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url })
      })
      if (!res.ok) throw new Error(res.statusText)
      const data = await res.json()
      addLog(`Started: ${JSON.stringify(data)}`)
      setIsConnected(true)
    } catch (e: any) {
      addLog(`Error starting: ${e.message}`)
    }
  }

  const sendCommand = async (cmd: string, args: string = '') => {
    addLog(`Sending command: ${cmd} ${args}`)
    try {
      const res = await fetch(`${API_URL}/trainer/command`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ command: cmd, args })
      })
      const data = await res.json()
      setCommandOutput(JSON.stringify(data, null, 2))
      addLog(`Success: ${data.result}`)
    } catch (e: any) {
      addLog(`Error: ${e.message}`)
      setCommandOutput(`Error: ${e.message}`)
    }
  }

  const runGeneratedScraper = async () => {
    addLog('Running generated scraper...')
    try {
      const res = await fetch(`${API_URL}/run/generated_scraper`, {
        method: 'POST'
      })
      const data = await res.json()
      addLog(`Scraper Finished with code ${data.returncode}`)
      setCommandOutput(`STDOUT:\n${data.stdout}\n\nSTDERR:\n${data.stderr}`)
    } catch (e: any) {
      addLog(`Error running scraper: ${e.message}`)
    }
  }

  return (
    <div className="min-h-screen bg-neutral-900 text-neutral-100 p-6 font-sans">
      <div className="max-w-6xl mx-auto space-y-6">

        {/* Header */}
        <div className="flex items-center justify-between border-b border-neutral-700 pb-4">
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <Terminal className="text-emerald-500" />
            Scraper Trainer
          </h1>
          <div className="flex items-center gap-2">
            <div className={`w-3 h-3 rounded-full ${isConnected ? 'bg-emerald-500 shadow-emerald-500/50 shadow-lg' : 'bg-red-500'}`} />
            <span className="text-sm text-neutral-400">{isConnected ? 'Connected' : 'Disconnected'}</span>
          </div>
        </div>

        {/* Start Control */}
        <div className="bg-neutral-800/50 p-4 rounded-xl border border-neutral-700 flex gap-4 items-center">
          <input
            className="flex-1 bg-neutral-900 border border-neutral-700 rounded px-3 py-2 focus:ring-2 focus:ring-emerald-500 outline-none"
            value={url}
            onChange={e => setUrl(e.target.value)}
            placeholder="Start URL..."
          />
          <button
            onClick={startTrainer}
            className="bg-emerald-600 hover:bg-emerald-500 text-white px-6 py-2 rounded-lg font-medium flex items-center gap-2 transition-all shadow-lg shadow-emerald-900/20">
            <Play size={18} />
            Start Session (Opens Browser)
          </button>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

          {/* Command Palette */}
          <div className="lg:col-span-2 space-y-4">
            <div className="bg-neutral-800/30 p-4 rounded-xl border border-neutral-700 space-y-4">
              <h2 className="font-semibold text-lg text-neutral-300">Commands</h2>

              {/* Actions Grid */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">

                {/* Click */}
                <div className="bg-neutral-900 p-3 rounded-lg border border-neutral-800 space-y-2">
                  <div className="flex items-center gap-2 text-emerald-400 font-medium"><MousePointer size={16} /> Click</div>
                  <input placeholder="Selector or Text" className="w-full bg-neutral-800 px-2 py-1 rounded text-sm mb-1" value={clickSelector} onChange={e => setClickSelector(e.target.value)} />
                  <button onClick={() => sendCommand('click', `"${clickSelector}"`)} className="w-full bg-neutral-700 hover:bg-neutral-600 py-1 rounded text-sm transition-colors">Execute Click</button>
                </div>

                {/* Type */}
                <div className="bg-neutral-900 p-3 rounded-lg border border-neutral-800 space-y-2">
                  <div className="flex items-center gap-2 text-blue-400 font-medium"><Type size={16} /> Type</div>
                  <input placeholder="Selector/Label" className="w-full bg-neutral-800 px-2 py-1 rounded text-sm" value={typeSelector} onChange={e => setTypeSelector(e.target.value)} />
                  <input placeholder="Value to type" className="w-full bg-neutral-800 px-2 py-1 rounded text-sm" value={typeValue} onChange={e => setTypeValue(e.target.value)} />
                  <button onClick={() => sendCommand('type', `"${typeSelector}" "${typeValue}"`)} className="w-full bg-neutral-700 hover:bg-neutral-600 py-1 rounded text-sm transition-colors">Execute Type</button>
                </div>

                {/* Press Key */}
                <div className="bg-neutral-900 p-3 rounded-lg border border-neutral-800 space-y-2">
                  <div className="flex items-center gap-2 text-indigo-400 font-medium"><Code size={16} /> Press Key</div>
                  <input placeholder="Key (e.g. Enter)" className="w-full bg-neutral-800 px-2 py-1 rounded text-sm mb-1" value={pressKey} onChange={e => setPressKey(e.target.value)} />
                  <button onClick={() => sendCommand('press', pressKey)} className="w-full bg-neutral-700 hover:bg-neutral-600 py-1 rounded text-sm transition-colors">Execute Press</button>
                </div>

                {/* Wait & Scroll */}
                <div className="bg-neutral-900 p-3 rounded-lg border border-neutral-800 space-y-2">
                  <div className="flex items-center gap-2 text-orange-400 font-medium"><Clock size={16} /> Wait / Scroll</div>
                  <div className="flex gap-2">
                    <input className="w-16 bg-neutral-800 px-2 py-1 rounded text-sm" value={waitSecs} onChange={e => setWaitSecs(e.target.value)} />
                    <button onClick={() => sendCommand('wait', waitSecs)} className="flex-1 bg-neutral-700 hover:bg-neutral-600 py-1 rounded text-sm">Wait {waitSecs}s</button>
                  </div>
                  <button onClick={() => sendCommand('scroll')} className="w-full bg-neutral-700 hover:bg-neutral-600 py-1 rounded text-sm flex justify-center items-center gap-1"><ArrowDown size={14} /> Scroll Down</button>
                </div>

                {/* Other */}
                <div className="bg-neutral-900 p-3 rounded-lg border border-neutral-800 space-y-2">
                  <div className="flex items-center gap-2 text-purple-400 font-medium"><FileText size={16} /> Actions</div>
                  <button onClick={() => sendCommand('scrape')} className="w-full bg-neutral-700 hover:bg-neutral-600 py-1 rounded text-sm mb-1">Scrape Content</button>
                  <button onClick={() => sendCommand('finish')} className="w-full bg-green-900/50 text-green-400 hover:bg-green-900/80 py-1 rounded text-sm border border-green-800">Generate Script</button>
                </div>
              </div>

              {/* POD Command */}
              <div className="bg-neutral-900 p-3 rounded-lg border border-neutral-800 space-y-3 mt-4">
                <div className="flex items-center gap-2 text-pink-400 font-medium"><Search size={16} /> Pattern Oriented Discovery (POD)</div>
                <div className="grid grid-cols-3 gap-2">
                  <input placeholder="Selector (e.g. button)" className="bg-neutral-800 px-2 py-1 rounded text-sm" value={podSelector} onChange={e => setPodSelector(e.target.value)} />
                  <input placeholder="Attr (e.g. Date)" className="bg-neutral-800 px-2 py-1 rounded text-sm" value={podAttr} onChange={e => setPodAttr(e.target.value)} />
                  <input placeholder="Value (e.g. 1/1/2000)" className="bg-neutral-800 px-2 py-1 rounded text-sm" value={podVal} onChange={e => setPodVal(e.target.value)} />
                </div>
                <button onClick={() => sendCommand('pod', `${podSelector}|${podAttr}|${podVal}`)} className="w-full bg-neutral-700 hover:bg-neutral-600 py-1 rounded text-sm transition-colors">Run POD Search</button>
              </div>

            </div>

            {/* Scraper Runner */}
            <div className="bg-blue-900/10 p-4 rounded-xl border border-blue-900/30 flex items-center justify-between">
              <div>
                <h3 className="font-semibold text-blue-200">Run Generated Scraper</h3>
                <p className="text-xs text-blue-400">Executes generated_scraper.py (Visible Browser)</p>
              </div>
              <button onClick={runGeneratedScraper} className="bg-blue-600 hover:bg-blue-500 text-white px-4 py-2 rounded-lg text-sm font-medium shadow-lg shadow-blue-900/20">Run Scraper (Opens Browser)</button>
            </div>
          </div>

          {/* Logs Panel */}
          <div className="bg-neutral-950 rounded-xl border border-neutral-800 p-4 flex flex-col h-[600px]">
            <h2 className="font-semibold text-neutral-400 mb-2 text-sm uppercase tracking-wider">Console Output</h2>
            <div className="flex-1 overflow-auto space-y-1 font-mono text-xs text-neutral-300 p-2 bg-black/40 rounded">
              {logs.length === 0 && <span className="text-neutral-600 italic">No logs yet...</span>}
              {logs.map((log, i) => (
                <div key={i} className="border-b border-neutral-800/50 pb-1 mb-1 last:border-0">{log}</div>
              ))}
            </div>
            <div className="h-1/3 mt-4 border-t border-neutral-800 pt-2">
              <h3 className="text-xs text-neutral-500 mb-1">Last Response</h3>
              <pre className="text-xs text-green-400 overflow-auto h-full bg-neutral-900 p-2 rounded">{commandOutput}</pre>
            </div>
          </div>

        </div>
      </div>
    </div>
  )
}
