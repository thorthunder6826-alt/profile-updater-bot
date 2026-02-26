import { useState, useEffect } from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";

const slides = [
  {
    bg: "from-[#1a3a5c] to-[#0a1929]",
    title: "New Year, New Deals",
    subtitle: "Save big on top brands across all categories",
    cta: "Shop deals",
    accent: "#FFD814",
  },
  {
    bg: "from-[#1a4a2a] to-[#0a2910]",
    title: "Shop for your home",
    subtitle: "Kitchen, furniture, bedding & more",
    cta: "Explore now",
    accent: "#FFD814",
  },
  {
    bg: "from-[#4a1a2a] to-[#290a10]",
    title: "Valentine's Day gifts",
    subtitle: "Find the perfect present for everyone",
    cta: "Shop gifts",
    accent: "#FF6B6B",
  },
  {
    bg: "from-[#3a2a1a] to-[#1a1408]",
    title: "Electronics deals",
    subtitle: "Top tech at the lowest prices of the season",
    cta: "See all deals",
    accent: "#FFD814",
  },
];

export default function HeroBanner() {
  const [current, setCurrent] = useState(0);

  useEffect(() => {
    const timer = setInterval(() => {
      setCurrent((prev) => (prev + 1) % slides.length);
    }, 5000);
    return () => clearInterval(timer);
  }, []);

  const prev = () => setCurrent((c) => (c - 1 + slides.length) % slides.length);
  const next = () => setCurrent((c) => (c + 1) % slides.length);

  const slide = slides[current];

  return (
    <div className="relative w-full h-[280px] sm:h-[350px] md:h-[400px] overflow-hidden">
      {/* Background */}
      <div
        className={`absolute inset-0 bg-gradient-to-b ${slide.bg} transition-all duration-700`}
      />

      {/* Pattern overlay */}
      <div className="absolute inset-0 opacity-10">
        <div
          className="w-full h-full"
          style={{
            backgroundImage:
              "radial-gradient(circle at 25% 50%, rgba(255,255,255,0.15) 0%, transparent 50%), radial-gradient(circle at 75% 30%, rgba(255,255,255,0.1) 0%, transparent 40%)",
          }}
        />
      </div>

      {/* Content */}
      <div className="relative z-10 max-w-[1500px] mx-auto h-full flex items-center px-16">
        <div className="text-white max-w-lg">
          <h1 className="text-3xl sm:text-4xl md:text-5xl font-extrabold mb-3 leading-tight">
            {slide.title}
          </h1>
          <p className="text-lg sm:text-xl text-white/80 mb-6">{slide.subtitle}</p>
          <button
            className="px-8 py-3 rounded-full font-bold text-sm text-[#131921]"
            style={{ backgroundColor: slide.accent }}
          >
            {slide.cta}
          </button>
        </div>
      </div>

      {/* Fade bottom */}
      <div className="absolute bottom-0 left-0 right-0 h-32 bg-gradient-to-t from-[#E3E6E6] to-transparent z-10 pointer-events-none" />

      {/* Navigation arrows */}
      <button
        onClick={prev}
        className="absolute left-0 top-0 bottom-16 w-14 flex items-center justify-center z-20 text-white/60 hover:text-white transition-colors"
      >
        <ChevronLeft size={40} />
      </button>
      <button
        onClick={next}
        className="absolute right-0 top-0 bottom-16 w-14 flex items-center justify-center z-20 text-white/60 hover:text-white transition-colors"
      >
        <ChevronRight size={40} />
      </button>

      {/* Dots */}
      <div className="absolute bottom-36 left-1/2 -translate-x-1/2 flex gap-2 z-20">
        {slides.map((_, i) => (
          <button
            key={i}
            onClick={() => setCurrent(i)}
            className={`w-2.5 h-2.5 rounded-full transition-all ${
              i === current ? "bg-white scale-110" : "bg-white/40"
            }`}
          />
        ))}
      </div>
    </div>
  );
}
