"use client";

import React, { useState, useEffect, useRef } from "react";
import { motion, Variants } from "framer-motion";
import { CheckCircle, Zap } from "lucide-react";

const MotionDiv = motion.div;

interface StepItem {
  stepIndex: number;
  num: string;
  name: string;
  desc: string;
}

export default function HowItWorks() {
  const [activeStep, setActiveStep] = useState<number>(0);
  const [hoveredStep, setHoveredStep] = useState<number | null>(null);
  const [beamOffset, setBeamOffset] = useState<number>(1);

  // Refs for tracking animation state across renders without breaking requestAnimationFrame
  const hoveredStepRef = useRef<number | null>(null);
  hoveredStepRef.current = hoveredStep;

  const accumulatedTimeRef = useRef<number>(0);
  const lastNowRef = useRef<number>(0);

  // Synchronized 60fps animation loop using requestAnimationFrame
  // Automatically pauses when any card is hovered, and seamlessly resumes when cursor leaves
  useEffect(() => {
    let animationFrameId: number;
    const cycleDuration = 22500; // 22.5 seconds total for all 9 steps (~2.5s per step - slow & smooth)

    const updateAnimation = (now: number) => {
      if (lastNowRef.current === 0) {
        lastNowRef.current = now;
      }
      const delta = now - lastNowRef.current;
      lastNowRef.current = now;

      if (hoveredStepRef.current === null) {
        // No card hovered -> Continue continuous animation loop
        accumulatedTimeRef.current += delta;
        const progress = (accumulatedTimeRef.current % cycleDuration) / cycleDuration;

        setBeamOffset(1 - progress);
        const currentStep = Math.min(8, Math.floor(progress * 9));
        setActiveStep(currentStep);
      } else {
        // Card is hovered -> PAUSE animation & highlight the hovered card!
        const targetStep = hoveredStepRef.current;
        setActiveStep(targetStep);
        setBeamOffset(1 - targetStep / 9);
      }

      animationFrameId = requestAnimationFrame(updateAnimation);
    };

    animationFrameId = requestAnimationFrame(updateAnimation);
    return () => cancelAnimationFrame(animationFrameId);
  }, []);

  // 9 Steps ordered in an S-shaped flow (Middle row physically reversed: 06, 05, 04)
  const gridSteps: StepItem[] = [
    // Top Row (Left to Right S-Flow: 01 -> 02 -> 03)
    { stepIndex: 0, num: "01", name: "Organization", desc: "Initialize your secure SaaS tenant" },
    { stepIndex: 1, num: "02", name: "AWS", desc: "Select target cloud environments" },
    { stepIndex: 2, num: "03", name: "CloudTrail", desc: "Ingest security audit trail logs" },

    // Middle Row (Right to Left S-Flow: 06 <- 05 <- 04)
    { stepIndex: 5, num: "06", name: "Risk Engine", desc: "Evaluate risk factor weights" },
    { stepIndex: 4, num: "05", name: "Graph Intelligence", desc: "Map active relationship links in Neo4j" },
    { stepIndex: 3, num: "04", name: "Identity Discovery", desc: "Discover machine roles & service users" },

    // Bottom Row (Left to Right S-Flow: 07 -> 08 -> 09)
    { stepIndex: 6, num: "07", name: "AI Copilot", desc: "Query machine profiles with natural AI reasoning" },
    { stepIndex: 7, num: "08", name: "Executive Dashboard", desc: "Monitor live metrics & blast radius graphs" },
    { stepIndex: 8, num: "09", name: "Remediation", desc: "Apply least privilege controls" }
  ];

  const containerVariants: Variants = {
    hidden: {},
    visible: {
      transition: { staggerChildren: 0.05 }
    }
  };

  const itemVariants: Variants = {
    hidden: { opacity: 0, y: 15 },
    visible: { opacity: 1, y: 0, transition: { duration: 0.5, ease: [0.16, 1, 0.3, 1] } }
  };

  // S-pipe SVG path string connecting all 9 cards including curved turn arcs
  const pipePathD = "M 166 100 L 500 100 L 833 100 C 970 100, 970 300, 833 300 L 500 300 L 166 300 C 30 300, 30 500, 166 500 L 500 500 L 833 500";

  return (
    <section id="how-it-works" className="w-full py-24 relative z-10 overflow-hidden bg-[#FEF8E8]/40 border-y border-[#E8C4E3]/40">
      <div className="max-w-[1100px] mx-auto px-6 relative">
        
        {/* Section Header */}
        <div className="text-center mb-16 relative z-10">
          <div className="inline-flex items-center justify-center px-4 py-1.5 rounded-full text-[#9D288E] text-[13px] font-bold tracking-[0.04em] bg-[#F5E6F3] border border-[#E5C6E1] mb-4 shadow-2xs">
            <Zap className="w-3.5 h-3.5 mr-1.5 text-[#9D288E] animate-pulse" />
            INGESTION TO RESOLUTION
          </div>
          <h2 className="font-[family-name:var(--font-jakarta)] font-extrabold text-3xl md:text-5xl text-[#2A1B28]">
            How SentinelAI Works
          </h2>
          <p className="text-[#5A4B58] text-base md:text-lg max-w-2xl mx-auto mt-4 font-normal">
            A continuous automated pipeline engineered to transform raw API log events into real-time threat intelligence.
          </p>
        </div>

        {/* Outer Container containing Grid + S-Pipe */}
        <div className="relative">
          
          {/* S-SHAPED PIPE SVG WITH BALANCED LIGHTER GLOWING LIGHT BEAM */}
          <div className="hidden md:block absolute inset-0 pointer-events-none z-0">
            <svg
              className="w-full h-full"
              viewBox="0 0 1000 600"
              preserveAspectRatio="none"
            >
              <defs>
                {/* Soft Ambient Glow Filter */}
                <filter id="softBeamGlow" x="-30%" y="-30%" width="160%" height="160%">
                  <feGaussianBlur stdDeviation="7" result="blur" />
                  <feMerge>
                    <feMergeNode in="blur" />
                    <feMergeNode in="SourceGraphic" />
                  </feMerge>
                </filter>

                {/* Elegant Magenta/Purple Light Beam Gradient */}
                <linearGradient id="softBeamGradient" x1="0%" y1="0%" x2="100%" y2="0%">
                  <stop offset="0%" stopColor="#C531B9" stopOpacity="0" />
                  <stop offset="35%" stopColor="#C531B9" stopOpacity="0.6" />
                  <stop offset="70%" stopColor="#FF66EF" stopOpacity="0.95" />
                  <stop offset="90%" stopColor="#FFFFFF" stopOpacity="0.9" />
                  <stop offset="100%" stopColor="#9D288E" stopOpacity="0" />
                </linearGradient>
              </defs>

              {/* Outer Translucent Glass Pipe Tube */}
              <path
                d={pipePathD}
                fill="none"
                stroke="#E8C4E3"
                strokeWidth="14"
                strokeLinecap="round"
                strokeLinejoin="round"
                opacity="0.5"
              />

              {/* Inner Pipe Track Line */}
              <path
                d={pipePathD}
                fill="none"
                stroke="#9D288E"
                strokeWidth="3"
                strokeLinecap="round"
                strokeLinejoin="round"
                opacity="0.25"
              />

              {/* ELEGANT BALANCED LIGHT BEAM STREAK */}
              <path
                d={pipePathD}
                fill="none"
                stroke="url(#softBeamGradient)"
                strokeWidth="9"
                strokeLinecap="round"
                strokeLinejoin="round"
                pathLength={1}
                strokeDasharray="0.16 0.84"
                strokeDashoffset={beamOffset}
                filter="url(#softBeamGlow)"
              />

              {/* Soft Center Highlight Core */}
              <path
                d={pipePathD}
                fill="none"
                stroke="#FFFFFF"
                strokeWidth="3"
                strokeLinecap="round"
                strokeLinejoin="round"
                pathLength={1}
                strokeDasharray="0.10 0.90"
                strokeDashoffset={beamOffset}
                opacity="0.75"
              />
            </svg>
          </div>

          {/* Stepper Grid (3x3 Layout with Middle Row Reversed) */}
          <MotionDiv 
            variants={containerVariants}
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true, margin: "-100px" }}
            onMouseLeave={() => setHoveredStep(null)}
            className="grid grid-cols-1 md:grid-cols-3 gap-6 relative z-10"
          >
            {gridSteps.map((s, idx) => {
              // Calculate continuous position of beam along steps (0.0 to 9.0)
              const beamStepPos = (1 - beamOffset) * 9;
              let dist = Math.abs(beamStepPos - s.stepIndex);
              if (dist > 4.5) dist = 9 - dist;

              // Gaussian bell curve for continuous wave intensity (0.0 to 1.0)
              const autoIntensity = Math.exp(-Math.pow(dist / 0.75, 2));

              let intensity = autoIntensity;
              if (hoveredStep !== null) {
                intensity = hoveredStep === s.stepIndex ? 1 : autoIntensity * 0.15;
              }

              // Clamp intensity between 0 and 1
              intensity = Math.max(0, Math.min(1, intensity));

              // Compute smooth interpolated colors & dimensions
              const rBorder = Math.round(232 - intensity * 35);
              const gBorder = Math.round(196 - intensity * 147);
              const bBorder = Math.round(227 - intensity * 42);
              const aBorder = (0.5 + intensity * 0.35).toFixed(2);

              const translateY = -(intensity * 4).toFixed(2);
              const scale = (1 + intensity * 0.008).toFixed(4);
              const shadowBlur = Math.round(6 + intensity * 18);
              const shadowAlpha = (intensity * 0.14).toFixed(3);

              return (
                <MotionDiv 
                  key={idx} 
                  variants={itemVariants}
                  onMouseEnter={() => setHoveredStep(s.stepIndex)}
                  onMouseLeave={() => setHoveredStep(null)}
                  style={{
                    transform: `translateY(${translateY}px) scale(${scale})`,
                    borderColor: `rgba(${rBorder}, ${gBorder}, ${bBorder}, ${aBorder})`,
                    boxShadow: intensity > 0.05 
                      ? `0 6px ${shadowBlur}px -2px rgba(197, 49, 185, ${shadowAlpha}), 0 2px 6px rgba(0,0,0,0.02)` 
                      : "0 1px 3px rgba(0, 0, 0, 0.03)",
                    transition: "transform 400ms cubic-bezier(0.16, 1, 0.3, 1), border-color 400ms ease-out, box-shadow 400ms ease-out, background-color 400ms ease-out"
                  }}
                  className={`rounded-[22px] p-6 flex flex-col justify-between cursor-pointer relative overflow-hidden ${
                    intensity > 0.4 ? "bg-white" : "bg-[#FAF5ED]"
                  }`}
                >
                  {/* Glowing background highlight smoothly crossfading via opacity */}
                  <div
                    style={{ opacity: intensity, transition: "opacity 400ms ease-out" }}
                    className="absolute inset-0 pointer-events-none bg-gradient-to-br from-[#C531B9]/10 via-[#9D288E]/4 to-amber-500/5"
                  />

                  <div className="relative z-10 pointer-events-none">
                    {/* Header Row: Step Badge + Checkmark */}
                    <div className="flex items-center justify-between mb-4">
                      {/* Step Badge Container with smooth dual-layer crossfade */}
                      <div className="relative inline-flex items-center">
                        <span
                          style={{ opacity: 1 - intensity * 0.85, transition: "opacity 400ms ease-out" }}
                          className="text-[11px] font-extrabold tracking-wider uppercase rounded-md px-3 py-1 text-[#9D288E] bg-[#F5E6F3] border border-[#E5C6E1]"
                        >
                          STEP {s.num}
                        </span>
                        <span
                          style={{ opacity: intensity, transition: "opacity 400ms ease-out" }}
                          className="absolute inset-0 text-[11px] font-extrabold tracking-wider uppercase rounded-md px-3 py-1 text-white bg-gradient-to-r from-[#C531B9] to-[#9D288E] shadow-sm shadow-[#9D288E]/20 flex items-center justify-center"
                        >
                          STEP {s.num}
                        </span>
                      </div>

                      {/* Checkmark Container with smooth dual-layer crossfade */}
                      <div className="relative w-7 h-7">
                        <div
                          style={{ opacity: 1 - intensity * 0.85, transition: "opacity 400ms ease-out" }}
                          className="absolute inset-0 rounded-full flex items-center justify-center bg-[#FAF5ED] text-[#E5C6E1]"
                        >
                          <CheckCircle className="w-4 h-4 text-[#D6B5D2]" />
                        </div>
                        <div
                          style={{ opacity: intensity, transition: "opacity 400ms ease-out" }}
                          className="absolute inset-0 rounded-full flex items-center justify-center bg-[#F3D5EE] text-[#8A1E7B] shadow-2xs"
                        >
                          <CheckCircle className="w-4 h-4 text-[#8A1E7B]" />
                        </div>
                      </div>
                    </div>

                    {/* Step Title */}
                    <h3 className="font-[family-name:var(--font-jakarta)] text-lg font-extrabold text-[#2A1B28] mb-2">
                      {s.name}
                    </h3>

                    {/* Description */}
                    <p className="text-xs text-[#5A4B58] leading-relaxed font-normal">
                      {s.desc}
                    </p>
                  </div>
                </MotionDiv>
              );
            })}
          </MotionDiv>
        </div>
      </div>
    </section>
  );
}
