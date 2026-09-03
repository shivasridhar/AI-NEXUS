"use client";

import Link from "next/link";
import Image from "next/image";
import { ArrowRight } from "lucide-react";

export default function Hero() {
  return (
    <section className="relative z-10 w-full min-h-[calc(100vh-120px)] flex flex-col lg:flex-row items-center pt-[120px] pb-20 overflow-hidden bg-[#FFFDF9]">
      
      {/* Left Column (Text Content) - 45% width */}
      <div className="w-full lg:w-[45%] flex flex-col items-start px-6 lg:pl-[100px] relative z-20">

        <h1 className="font-[family-name:var(--font-jakarta)] font-extrabold text-[42px] sm:text-[52px] lg:text-[62px] leading-[1.08] text-[#2A1B28] tracking-tight">
          Turn cloud <span className="text-[#C531B9] underline decoration-[#E8C4E3] underline-offset-8">identity risks</span> into continuous <span className="text-[#8E2880]">protection</span>
        </h1>

        <p className="text-[17px] text-[#5A4B58] max-w-[480px] mt-6 leading-[1.65] font-normal">
          SentinelAI continuously discovers machine identities, maps privilege attack paths with Neo4j graph intelligence, and resolves security anomalies in real time.
        </p>

        <div className="mt-8 flex flex-col sm:flex-row items-center gap-4">
          <Link
            href="/signup"
            className="group flex items-center justify-between rounded-full bg-gradient-to-r from-[#C531B9] to-[#9D288E] text-white pl-3 pr-7 py-3 shadow-lg shadow-[#C531B9]/25 hover:shadow-xl hover:shadow-[#C531B9]/35 transition-all duration-300 hover:scale-[1.02]"
          >
            <div className="w-8 h-8 rounded-full bg-white/20 flex items-center justify-center mr-4 transition-transform group-hover:scale-110">
              <ArrowRight className="w-4 h-4 text-white" strokeWidth={3} />
            </div>
            <span className="font-bold text-[16px] tracking-wide">Try SentinelAI Free</span>
          </Link>
        </div>
      </div>

      {/* Right Column (Static 3D Artwork with Top/Bottom/Left/Right 4-Edge Fade Masking) - 55% width */}
      <div className="w-full lg:w-[55%] h-[400px] sm:h-[500px] lg:h-[700px] relative mt-12 lg:mt-0 z-10 flex items-center justify-center pointer-events-none">
        <HeroIllustration />
      </div>

    </section>
  );
}

function HeroIllustration() {
  return (
    <div className="w-full h-full relative flex items-center justify-center">
      {/* Soft Ambient Purple Background Glow */}
      <div className="absolute w-[70%] h-[70%] rounded-full bg-gradient-to-r from-[#C531B9]/15 via-[#9D288E]/10 to-amber-500/5 blur-[110px] pointer-events-none" />

      {/* Fully Static 3D Graphic with Elliptical 4-Edge Soft Fade Masking */}
      <div
        style={{
          maskImage: "radial-gradient(ellipse 68% 55% at 50% 50%, black 20%, transparent 75%)",
          WebkitMaskImage: "radial-gradient(ellipse 68% 55% at 50% 50%, black 20%, transparent 75%)"
        }}
        className="w-[110%] lg:w-[125%] h-auto relative max-w-none flex items-center justify-center"
      >
        <Image
          src="/images/hero_cloud_security_v2.jpg"
          alt="SentinelAI Enterprise Cloud Identity Security Illustration"
          width={1400}
          height={800}
          priority
          className="w-full h-auto object-contain mix-blend-multiply"
        />
      </div>
    </div>
  );
}
