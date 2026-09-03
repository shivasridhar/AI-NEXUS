"use client";

import Image from "next/image";
import { Users, Target, HelpCircle, Network, Shield } from "lucide-react";

export default function WhyIdentitySecurity() {
  return (
    <section id="security" className="w-full py-16 md:py-24 bg-white border-b border-amber-100/40 relative z-10 overflow-hidden">
      {/* Background Soft Ambient Glow */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[900px] h-[650px] bg-gradient-to-r from-purple-100/30 via-amber-50/40 to-purple-100/30 blur-[140px] rounded-full pointer-events-none" />

      <div className="max-w-[1360px] mx-auto px-4 md:px-8 relative z-10">
        
        {/* Section Heading */}
        <div className="text-center mb-12 md:mb-16">
          <div className="inline-flex items-center justify-center px-4 py-1.5 rounded-full text-[#8E24AA] text-[13px] font-bold tracking-[0.05em] bg-[#F3E5F5] border border-purple-200/60 mb-4 uppercase">
            Understanding The Risk
          </div>
          <h2 className="font-[family-name:var(--font-jakarta)] font-extrabold text-3xl md:text-5xl text-[#2D124D] mb-4 tracking-tight">
            Why Machine Identity Security?
          </h2>
          <p className="text-[#6A5378] text-base md:text-lg max-w-2xl mx-auto font-medium">
            Traditional tools focus on human access keys. But today, the real risk lies in machine integration tokens and service execution roles.
          </p>
        </div>

        {/* 3-Column Diagram (Left Cards - Center Robot Mascot - Right Cards) */}
        <div className="flex flex-col lg:flex-row items-stretch justify-between gap-8 lg:gap-2 relative min-h-[620px]">
          
          {/* Left Cards Column - Higher Z-Index so cards sit ON TOP of center robot image */}
          <div className="w-full lg:w-[35%] flex flex-col justify-between gap-8 md:gap-10 z-20 relative">
            {/* Card 1: Top Left */}
            <div className="relative bg-[#FFFDF8] border border-[#F5E8D6] rounded-[24px] p-6 md:p-8 shadow-[0_10px_30px_-8px_rgba(215,185,155,0.22)] transition-transform duration-300 hover:-translate-y-1 flex-1 flex flex-col justify-center z-20">
              <div className="w-12 h-12 rounded-[16px] bg-[#F3E5F5] flex items-center justify-center mb-4 flex-shrink-0 shadow-inner">
                <Users className="w-6 h-6 text-[#9C27B0]" />
              </div>
              <h3 className="font-[family-name:var(--font-jakarta)] text-lg font-bold text-[#3A1854] mb-2.5 leading-snug">
                Machine Identities outnumber humans 10:1
              </h3>
              <p className="text-[14px] text-[#5C4A68] leading-relaxed">
                Every cloud microservice, Lambda execution role, API key, database connector, and container instance requires access policies. They represent the largest security footprint.
              </p>
            </div>

            {/* Card 2: Bottom Left */}
            <div className="relative bg-[#FFFDF8] border border-[#F5E8D6] rounded-[24px] p-6 md:p-8 shadow-[0_10px_30px_-8px_rgba(215,185,155,0.22)] transition-transform duration-300 hover:-translate-y-1 flex-1 flex flex-col justify-center z-20">
              <div className="w-12 h-12 rounded-[16px] bg-[#F3E5F5] flex items-center justify-center mb-4 flex-shrink-0 shadow-inner">
                <HelpCircle className="w-6 h-6 text-[#9C27B0]" />
              </div>
              <h3 className="font-[family-name:var(--font-jakarta)] text-lg font-bold text-[#3A1854] mb-2.5 leading-snug">
                Traditional tooling is blind to context
              </h3>
              <p className="text-[14px] text-[#5C4A68] leading-relaxed">
                Traditional IAM analyzers check if a single policy is over-privileged, but they cannot see if a role can assume another role that eventually accesses a critical database.
              </p>
            </div>
          </div>

          {/* Center Column: Robot Mascot Image - Set Z-0 so it sits BEHIND cards */}
          <div className="w-full lg:w-[30%] relative flex flex-col items-center justify-between py-4 lg:py-2 z-0">
            
            {/* "Cloud Application Security" Label */}
            <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-[#F3E5F5]/90 border border-purple-200 shadow-sm mb-2 z-20">
              <Shield className="w-4 h-4 text-[#9C27B0]" />
              <span className="font-[family-name:var(--font-jakarta)] font-extrabold text-[13px] md:text-[14px] text-[#3B1354] tracking-tight whitespace-nowrap">
                Cloud Application Security
              </span>
            </div>

            {/* Robot Mascot Image - Large & Layered Behind Cards */}
            <div className="relative w-full flex-1 flex items-center justify-center z-0">
              <Image
                src="/images/robot_mascot_connect.png"
                alt="Cloud Application Security Robot"
                width={700}
                height={520}
                priority
                className="w-full h-auto max-h-[520px] object-contain transform scale-110 lg:scale-125 transition-transform duration-300 mix-blend-multiply pointer-events-none"
              />
            </div>

          </div>

          {/* Right Cards Column - Higher Z-Index so cards sit ON TOP of center robot image */}
          <div className="w-full lg:w-[35%] flex flex-col justify-between gap-8 md:gap-10 z-20 relative">
            {/* Card 3: Top Right */}
            <div className="relative bg-[#FFFDF8] border border-[#F5E8D6] rounded-[24px] p-6 md:p-8 shadow-[0_10px_30px_-8px_rgba(215,185,155,0.22)] transition-transform duration-300 hover:-translate-y-1 flex-1 flex flex-col justify-center z-20">
              <div className="w-12 h-12 rounded-[16px] bg-[#F3E5F5] flex items-center justify-center mb-4 flex-shrink-0 shadow-inner">
                <Target className="w-6 h-6 text-[#9C27B0]" />
              </div>
              <h3 className="font-[family-name:var(--font-jakarta)] text-lg font-bold text-[#3A1854] mb-2.5 leading-snug">
                They are prime targets for abuse
              </h3>
              <p className="text-[14px] text-[#5C4A68] leading-relaxed">
                Attackers look for stale keys or misconfigured permissions to move laterally. Unlike humans, machine accounts don't trigger multi-factor authentication (MFA).
              </p>
            </div>

            {/* Card 4: Bottom Right */}
            <div className="relative bg-[#FFFDF8] border border-[#F5E8D6] rounded-[24px] p-6 md:p-8 shadow-[0_10px_30px_-8px_rgba(215,185,155,0.22)] transition-transform duration-300 hover:-translate-y-1 flex-1 flex flex-col justify-center z-20">
              <div className="w-12 h-12 rounded-[16px] bg-[#F3E5F5] flex items-center justify-center mb-4 flex-shrink-0 shadow-inner">
                <Network className="w-6 h-6 text-[#9C27B0]" />
              </div>
              <h3 className="font-[family-name:var(--font-jakarta)] text-lg font-bold text-[#3A1854] mb-2.5 leading-snug">
                Why Graph Analysis is the only solution
              </h3>
              <p className="text-[14px] text-[#5C4A68] leading-relaxed">
                Security is a graph, not a list. By mapping identities and resources in Neo4j, SentinelAI uncovers indirect access paths that linear IAM scanning misses entirely.
              </p>
            </div>
          </div>

        </div>
      </div>
    </section>
  );
}


