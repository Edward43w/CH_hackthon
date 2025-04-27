import React, { useState, useEffect, useRef } from 'react'
import axios from 'axios'
import './style.css'

export default function App() {
  const [state, setState] = useState('idle')

  const [fullText, setFullText] = useState('請說「你好」來喚醒我')
  const [displayText, setDisplayText] = useState('')
  const [isListeningForCommand, setIsListeningForCommand] = useState(false)
  const [statusInterval, setStatusInterval] = useState(null)
  const typingInterval = 200

  const eyeL = useRef()
  const eyeR = useRef()
  const browL = useRef()
  const browR = useRef()
  const frownL = useRef()
  const frownR = useRef()
  const sweat = useRef()
  const mouth = useRef()
  const questions = useRef([])

  const hotword = '你好'
  const exitWord = '再見'
  const pauseWord = '暫停'
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition

  const hotwordRecog = useRef(null)
  const commandRecog = useRef(null)
  const speechSynthesisRef = useRef(window.speechSynthesis)
  const listeningRef = useRef(false)
  const isProcessingRef = useRef(false)
  const isSpeakingRef = useRef(false)
  
  
  useEffect(() => {
    let idx = 0
    setDisplayText('')
    if (!fullText) return
    const interval = setInterval(() => {
      setDisplayText(prev => prev + fullText.charAt(idx))
      idx++
      if (idx >= fullText.length) clearInterval(interval)
    }, typingInterval)
    return () => clearInterval(interval)
  }, [fullText])

  

  useEffect(() => {
    if (!SR) {
      setFullText('❌ 瀏覽器不支援 Web Speech API')
      return
    }
    startHotwordRecognition()
    return () => {
      hotwordRecog.current?.abort()
      commandRecog.current?.abort()
      speechSynthesisRef.current.cancel()
      if (statusInterval) clearInterval(statusInterval)
    }
  }, [])

  const startHotwordRecognition = () => {
    hotwordRecog.current = new SR()
    hotwordRecog.current.lang = 'zh-TW'
    hotwordRecog.current.continuous = true
    hotwordRecog.current.interimResults = false
    hotwordRecog.current.onresult = event => {
      const text = event.results[event.results.length - 1][0].transcript.trim()
      console.log('Hotword detected:', text)
      if (text.includes(hotword)) {
        hotwordRecog.current.stop()
        startCommandRecognition()
      }
    }
    hotwordRecog.current.onend = () => {
      if (!listeningRef.current) hotwordRecog.current.start()
    }
    hotwordRecog.current.start()
  }

  const startCommandRecognition = () => {
    listeningRef.current = true
    setIsListeningForCommand(true)
    setFullText('我在聽，請說出您的問題，說「再見」結束，或「暫停」停止')

    commandRecog.current = new SR()
    commandRecog.current.lang = 'zh-TW'
    commandRecog.current.continuous = true
    commandRecog.current.interimResults = false
    commandRecog.current.onresult = handleCommandResult
    commandRecog.current.onerror = e => {
      if (e.error !== 'aborted') console.warn('Command Error', e.error)
    }
    commandRecog.current.onend = () => {
      if (listeningRef.current) {
        try { commandRecog.current.start() } catch {}
      }
    }
    commandRecog.current.start()
  }

  const handleCommandResult = async event => {
    const text = event.results[event.results.length - 1][0].transcript.trim()
    console.log('Command detected:', text)

    // 優先識別退出與暫停指令
    if (text.includes(exitWord)) {
      finishCommandRecognition()
      return
    }
    if (text.includes(pauseWord)) {
      backToListening()
      return
    }

    // 若正在處理或語音中，忽略其他指令
    if (isProcessingRef.current || isSpeakingRef.current) {
      return
    }

    // 處理使用者指令
    isProcessingRef.current = true
    setIsListeningForCommand(false)
    commandRecog.current.stop()
    setFullText(`正在處理: ${text}`)
    await sendCommandToServer(text)
    isProcessingRef.current = false
  }

  const backToListening = () => {
    speechSynthesisRef.current.cancel()
    isProcessingRef.current = false
    isSpeakingRef.current = false
    setFullText('我在聽，請說出您的問題，說「再見」結束，或「暫停」停止')
    try { commandRecog.current.stop() } catch {}
    setTimeout(() => {
      if (listeningRef.current) startCommandRecognition()
    }, 500)
  }

  const finishCommandRecognition = () => {
    listeningRef.current = false
    isProcessingRef.current = false
    isSpeakingRef.current = false
    setIsListeningForCommand(false)
    setFullText('請說「你好」來喚醒我')
    commandRecog.current?.stop()
    hotwordRecog.current?.start()
  }

  const sendCommandToServer = async text => {
    try {
      await axios.post(`${import.meta.env.VITE_API_URL}/process_command`, { text })
      const interval = setInterval(async () => {
        const { data } = await axios.get(`${import.meta.env.VITE_API_URL}/audio_status`)
        if (data.has_new && data.reply) {
          setFullText(data.reply)
          speak(data.reply)
        }
        if (data.state === 'idle') {
          clearInterval(interval)
          setIsListeningForCommand(true)
        }
      }, 1000)
      setStatusInterval(interval)
    } catch (err) {
      console.error(err)
      setFullText('無法連接到後端')
      setIsListeningForCommand(true)
    }
  }

  const speak = text => {
    // 在語音播放時持續聆聽以偵測「暫停」指令
    if (listeningRef.current && commandRecog.current) {
      try { commandRecog.current.start() } catch {}
    }
    isSpeakingRef.current = true
    const ut = new SpeechSynthesisUtterance(text)
    ut.lang = 'zh-TW'
    ut.onend = () => {
      isSpeakingRef.current = false
      if (listeningRef.current) {
        setIsListeningForCommand(true)
        startCommandRecognition()
      }
    }
    speechSynthesisRef.current.cancel()
    speechSynthesisRef.current.speak(ut)
  }

  return (
    <div className="main-container">
      <h1>語音機器人</h1>
      <div className="status-indicator">
        <span>
          {isListeningForCommand
            ? '命令模式: 說指令或「再見」結束'
            : fullText.startsWith('正在處理')
            ? '處理中...'
            : '偵測熱詞: 說「你好」'}
        </span>
      </div>
      <div className="dialogue-box">
        <p>{displayText}</p>
      </div>
    </div>
  )
}