"use client";

export default function BackgroundEffects() {
  return (
    <div className="absolute inset-0 overflow-hidden pointer-events-none z-0">
      {/* Soft Ambient Background Orbs */}
      <div className="absolute top-[-10%] left-[-10%] w-[500px] h-[500px] rounded-full bg-amber-200/20 blur-[140px]" />
      <div className="absolute top-[35%] right-[-5%] w-[600px] h-[600px] rounded-full bg-purple-200/15 blur-[160px]" />
      <div className="absolute top-[65%] left-[-5%] w-[500px] h-[500px] rounded-full bg-pink-200/15 blur-[140px]" />
    </div>
  );
}
