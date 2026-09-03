"use client";

import { Cloud, FileCode, Cpu, GitBranch, ShieldCheck, BrainCircuit, LayoutDashboard } from "lucide-react";

function BeamArrow({ direction = "horizontal" }: { direction?: "horizontal" | "vertical" }) {
  return (
    <div
      className={`relative flex items-center justify-center shrink-0 ${
        direction === "vertical" ? "h-10 w-full my-2" : "w-8 xl:w-10 h-6 mx-0.5"
      }`}
    >
      {direction === "horizontal" ? (
        <div className="relative w-full h-[18px] flex items-center justify-center">
          {/* Track line background */}
          <div className="absolute w-full h-[2.5px] bg-[#E8C4E3] rounded-full overflow-hidden">
            {/* Beam of light flowing inside track */}
            <div className="w-full h-full bg-gradient-to-r from-transparent via-[#C531B9] to-[#FF80EF] shadow-[0_0_8px_#C531B9] animate-beam-pulse" />
          </div>

          {/* Glowing Arrowhead at destination */}
          <div className="absolute right-0 flex items-center justify-center text-[#C531B9] transform translate-x-1">
            <svg className="w-3.5 h-3.5 drop-shadow-[0_0_6px_#C531B9]" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M5 12h14M12 5l7 7-7 7" />
            </svg>
          </div>
        </div>
      ) : (
        <div className="relative h-full w-[18px] flex items-center justify-center">
          {/* Vertical Track line background */}
          <div className="absolute h-full w-[2.5px] bg-[#E8C4E3] rounded-full overflow-hidden">
            {/* Beam of light flowing down inside track */}
            <div className="w-full h-full bg-gradient-to-b from-transparent via-[#C531B9] to-[#FF80EF] shadow-[0_0_8px_#C531B9] animate-beam-pulse-vert" />
          </div>

          {/* Vertical Arrowhead at destination */}
          <div className="absolute bottom-0 flex items-center justify-center text-[#C531B9] transform translate-y-1">
            <svg className="w-3.5 h-3.5 drop-shadow-[0_0_6px_#C531B9]" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 5v14M5 12l7 7 7-7" />
            </svg>
          </div>
        </div>
      )}
    </div>
  );
}

export default function ArchitectureSection() {
  const topNodes = [
    { icon: <Cloud className="w-5 h-5 text-[#C531B9]" />, label: "Cloud Platforms", desc: "AWS, GCP, Azure API integrations" },
    { icon: <FileCode className="w-5 h-5 text-[#C531B9]" />, label: "CloudTrail logs", desc: "High throughput API access events" },
    { icon: <Cpu className="w-5 h-5 text-[#C531B9]" />, label: "Processing Engine", desc: "Stream parsing & sanitization" },
    { icon: <GitBranch className="w-5 h-5 text-[#C531B9]" />, label: "Neo4j Graph DB", desc: "Identity relationships mapping" },
    { icon: <ShieldCheck className="w-5 h-5 text-[#C531B9]" />, label: "Risk Engine", desc: "Signal heuristics scoring" },
    { icon: <BrainCircuit className="w-5 h-5 text-[#C531B9]" />, label: "Gemini AI", desc: "Contextual semantic logic" }
  ];

  const bottomNode = {
    icon: <LayoutDashboard className="w-5 h-5 text-[#C531B9]" />,
    label: "SecOps Dashboard",
    desc: "Real-time command center alerts"
  };

  const allNodes = [...topNodes, bottomNode];

  return (
    <section id="platform" className="w-full py-24 bg-[#FFFDF9] border-b border-[#E8C4E3]/60 relative z-10">
      <div className="max-w-[1280px] mx-auto px-4 sm:px-6">
        
        {/* Section Heading */}
        <div className="text-center mb-16">
          <div className="inline-flex items-center justify-center px-4 py-1.5 rounded-full text-[#9D288E] text-[13px] font-bold tracking-wider bg-[#F5E6F3] border border-[#E5C6E1] mb-4 shadow-2xs">
            SYSTEM ARCHITECTURE
          </div>
          <h2 className="font-[family-name:var(--font-jakarta)] font-extrabold text-3xl md:text-5xl text-[#2A1B28] mb-4">
            Security Graph Pipeline
          </h2>
          <p className="text-[#5A4B58] text-lg max-w-2xl mx-auto">
            A secure cloud infrastructure processing audit streams into graph assets in real time.
          </p>
        </div>

        {/* Desktop Pipeline Layout */}
        <div className="hidden lg:flex flex-col items-center">
          {/* Top Row of Cards with Beam Arrows strictly between cards */}
          <div className="flex items-center justify-center w-full">
            {topNodes.map((node, i) => (
              <div key={i} className="flex items-center">
                {/* Pipeline Card */}
                <div className="flex flex-col items-center p-4 rounded-2xl bg-white border border-[#E8C4E3] shadow-xs w-[145px] xl:w-[155px] text-center hover:border-[#C531B9] hover:shadow-md transition-all duration-300">
                  <div className="w-10 h-10 rounded-xl bg-[#F5E6F3]/60 border border-[#E8C4E3] flex items-center justify-center mb-3">
                    {node.icon}
                  </div>
                  <h3 className="font-[family-name:var(--font-jakarta)] text-[12px] font-extrabold text-[#2A1B28] mb-1 leading-tight">
                    {node.label}
                  </h3>
                  <p className="text-[10px] text-[#614D56] leading-tight font-normal">
                    {node.desc}
                  </p>
                </div>

                {/* Light Beam Arrow ONLY between adjacent cards in top row */}
                {i < topNodes.length - 1 && (
                  <BeamArrow direction="horizontal" />
                )}
              </div>
            ))}
          </div>

          {/* Vertical Connecting Light Beam Arrow down to SecOps Dashboard */}
          <BeamArrow direction="vertical" />

          {/* Bottom Card (SecOps Dashboard) */}
          <div className="flex flex-col items-center p-4 rounded-2xl bg-white border border-[#E8C4E3] shadow-xs w-[155px] text-center hover:border-[#C531B9] hover:shadow-md transition-all duration-300">
            <div className="w-10 h-10 rounded-xl bg-[#F5E6F3]/60 border border-[#E8C4E3] flex items-center justify-center mb-3">
              {bottomNode.icon}
            </div>
            <h3 className="font-[family-name:var(--font-jakarta)] text-[12px] font-extrabold text-[#2A1B28] mb-1 leading-tight">
              {bottomNode.label}
            </h3>
            <p className="text-[10px] text-[#614D56] leading-tight font-normal">
              {bottomNode.desc}
            </p>
          </div>
        </div>

        {/* Mobile / Tablet Vertical Stack Layout */}
        <div className="flex lg:hidden flex-col items-center max-w-[280px] mx-auto">
          {allNodes.map((node, i) => (
            <div key={i} className="flex flex-col items-center w-full">
              {/* Card */}
              <div className="flex flex-col items-center p-4 rounded-2xl bg-white border border-[#E8C4E3] shadow-xs w-full text-center hover:border-[#C531B9] transition-all">
                <div className="w-10 h-10 rounded-xl bg-[#F5E6F3]/60 border border-[#E8C4E3] flex items-center justify-center mb-3">
                  {node.icon}
                </div>
                <h3 className="font-[family-name:var(--font-jakarta)] text-xs font-extrabold text-[#2A1B28] mb-1">
                  {node.label}
                </h3>
                <p className="text-[11px] text-[#614D56] leading-tight font-normal">
                  {node.desc}
                </p>
              </div>

              {/* Vertical Light Beam Arrow ONLY between cards */}
              {i < allNodes.length - 1 && (
                <BeamArrow direction="vertical" />
              )}
            </div>
          ))}
        </div>

      </div>
    </section>
  );
}
