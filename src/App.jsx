import { useEffect } from 'react'
import Navbar from './components/Navbar.jsx'
import Hero from './components/Hero.jsx'
import CourseContent from './components/CourseContent.jsx'
import Features from './components/Features.jsx'
import Pricing from './components/Pricing.jsx'
import Signup from './components/Signup.jsx'
import Footer from './components/Footer.jsx'
import { boot } from './motion/app.js'

export default function App() {
  // The motion layer mutates the DOM (SplitText, canvas), so it boots once and React never re-renders these trees.
  useEffect(() => boot(), [])

  return (
    <>
      <div data-start="hidden" className="pw">
        <Navbar />
        <div className="w">
          <Hero />
          <CourseContent />
          <Features />
          <Pricing />
          <Signup />
          <Footer />
        </div>
      </div>
      <div className="canvas w-embed">
        <div data-gl="c" className="canvas" style={{ position: 'fixed', width: '100vw', height: '100vh' }}></div>
      </div>
    </>
  )
}
