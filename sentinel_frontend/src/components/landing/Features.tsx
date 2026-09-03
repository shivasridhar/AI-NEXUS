"use client";

import React, { useRef, useState } from "react";
import { motion, useMotionValue, useTransform, useSpring, Variants } from "framer-motion";
import { Users, GitBranch, ShieldAlert, BrainCircuit, ClipboardCheck, FileBarChart, Cloud } from "lucide-react";

const MotionDiv = motion.div;

interface ModuleItem {
  icon: React.ReactNode;
  title: string;
  value: string;
  desc: string;
}

const containerVariants: Variants = {
  hidden: {},
  visible: {
    transition: { staggerChildren: 0.06 }
  }
};

const cardVariants: Variants = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.6, ease: [0.16, 1, 0.3, 1] } }
};

function InteractiveFeatureCard({ m, idx }: { m: ModuleItem; idx: number }) {
  const cardRef = useRef<HTMLDivElement>(null);
  const [isHovered, setIsHovered] = useState(false);

  // Normalized mouse position [0, 1]
  const x = useMotionValue(0.5);
  const y = useMotionValue(0.5);

  // Smooth, gentle spring physics configuration to prevent any speed spikes (smooth, silky motion)
  const masterSpringConfig = { stiffness: 75, damping: 24, mass: 0.9 };
  const iconSpringConfig = { stiffness: 85, damping: 25, mass: 0.9 };

  // Master card 3D tilt angles based on mouse tracking (subtle and smooth)
  const mouseRotateX = useSpring(useTransform(y, [0, 1], [3.5, -3.5]), masterSpringConfig);
  const mouseRotateY = useSpring(useTransform(x, [0, 1], [-3.5, 3.5]), masterSpringConfig);

  // Base hover state: Master Card levitates slowly (-8px) and tilts slightly (-2 deg)
  const masterTiltZ = useSpring(0, masterSpringConfig);
  const masterY = useSpring(0, masterSpringConfig);

  // Smaller Icon Card: Levitates UP (-5px) and tilts in the OPPOSITE DIRECTION (+4.5 deg & inverted 3D rotation)
  const iconRotateX = useSpring(useTransform(y, [0, 1], [-7, 7]), iconSpringConfig);
  const iconRotateY = useSpring(useTransform(x, [0, 1], [7, -7]), iconSpringConfig);
  const iconTiltZ = useSpring(0, iconSpringConfig);
  const iconY = useSpring(0, iconSpringConfig);

  const handleMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!cardRef.current) return;
    const rect = cardRef.current.getBoundingClientRect();
    x.set((e.clientX - rect.left) / rect.width);
    y.set((e.clientY - rect.top) / rect.height);
  };

  const handleMouseEnter = () => {
    setIsHovered(true);
    // Smooth master card levitation & counter-clockwise tilt
    masterY.set(-8);
    masterTiltZ.set(-2);

    // Smooth smaller icon card levitation & OPPOSITE clockwise tilt
    iconY.set(-5);
    iconTiltZ.set(4.5);
  };

  const handleMouseLeave = () => {
    setIsHovered(false);
    x.set(0.5);
    y.set(0.5);
    masterY.set(0);
    masterTiltZ.set(0);
    iconY.set(0);
    iconTiltZ.set(0);
  };

  return (
    <MotionDiv 
      variants={cardVariants}
      className={idx === 3 ? "md:col-span-2 lg:col-span-2" : ""}
      style={{ perspective: 1000 }}
    >
      <motion.div
        ref={cardRef}
        onMouseMove={handleMouseMove}
        onMouseEnter={handleMouseEnter}
        onMouseLeave={handleMouseLeave}
        style={{
          rotateX: isHovered ? mouseRotateX : 0,
          rotateY: isHovered ? mouseRotateY : 0,
          rotateZ: masterTiltZ,
          y: masterY,
          transformStyle: "preserve-3d",
        }}
        className={`p-7 flex flex-col justify-between rounded-[22px] transition-colors duration-500 relative bg-[#FAF5ED] border border-[#E8C4E3] cursor-pointer select-none ${
          isHovered
            ? "border-[#9D288E] shadow-2xl shadow-[#9D288E]/12 bg-[#FFFDF9]"
            : "shadow-sm hover:shadow-md"
        }`}
      >
        {/* Ambient sheen backdrop effect */}
        <div
          className={`absolute inset-0 rounded-[22px] pointer-events-none transition-opacity duration-700 bg-gradient-to-br from-[#9D288E]/5 via-transparent to-amber-500/5 ${
            isHovered ? "opacity-100" : "opacity-0"
          }`}
        />

        <div>
          {/* Header Row: Icon (Smaller Card) + Value Badge */}
          <div className="flex items-center justify-between mb-6 pointer-events-none">
            
            {/* SMALLER CARD: Contains Logo/Icon - Levitates & Tilts in OPPOSITE Direction */}
            <motion.div
              style={{
                rotateX: isHovered ? iconRotateX : 0,
                rotateY: isHovered ? iconRotateY : 0,
                rotateZ: iconTiltZ,
                y: iconY,
                transformStyle: "preserve-3d",
              }}
              className={`w-12 h-12 rounded-xl flex items-center justify-center transition-colors duration-500 ${
                isHovered
                  ? "bg-[#F3D5EE] border border-[#9D288E] shadow-lg shadow-[#9D288E]/20 text-[#8A1E7B]"
                  : "bg-[#F5E6F3] border border-[#E5C6E1] text-[#9D288E]"
              }`}
            >
              {m.icon}
            </motion.div>

            {/* Pill Badge */}
            <span className="text-[10px] font-extrabold text-[#9D288E] tracking-wider uppercase bg-[#FAF5ED] border border-[#E5C6E1] rounded-full px-3 py-1 shadow-2xs">
              {m.value}
            </span>
          </div>

          {/* Title */}
          <h3 className="font-[family-name:var(--font-jakarta)] text-xl font-extrabold text-[#2A1B28] mb-2.5 tracking-tight pointer-events-none">
            {m.title}
          </h3>

          {/* Description */}
          <p className="text-[#5A4B58] text-sm leading-relaxed font-normal pointer-events-none">
            {m.desc}
          </p>
        </div>
      </motion.div>
    </MotionDiv>
  );
}

export default function Features() {
  const modules: ModuleItem[] = [
    {
      icon: <Users className="w-5 h-5" />,
      title: "Identity Center",
      value: "Central Inventory",
      desc: "Automatically map and profile all active machine identities, IAM roles, and compute service accounts across your cloud environment."
    },
    {
      icon: <GitBranch className="w-5 h-5" />,
      title: "Threat Graph",
      value: "Attack Paths",
      desc: "Visualize chained privilege escalation paths. Locate exactly how an attacker can hop from a compute instance to critical data stores."
    },
    {
      icon: <ShieldAlert className="w-5 h-5" />,
      title: "Risk Center",
      value: "Prioritize Vulnerabilities",
      desc: "Evaluate risks in real time based on usage, misconfigurations, and external exposure. Prioritize fixing critical anomalies first."
    },
    {
      icon: <BrainCircuit className="w-5 h-5" />,
      title: "SentinelAI Copilot",
      value: "AI Investigation",
      desc: "Query machine identities and cloud activities in natural language. Generates executive reports and incident triage details instantly."
    },
    {
      icon: <ClipboardCheck className="w-5 h-5" />,
      title: "Compliance Monitor",
      value: "Continuous Audits",
      desc: "Track cloud posture compliance metrics against industry frameworks (SOC 2, ISO 27001, HIPAA, and CIS benchmarks) automatically."
    },
    {
      icon: <FileBarChart className="w-5 h-5" />,
      title: "Reports Hub",
      value: "Export Data",
      desc: "Create and schedule executive summaries, audits, and compliance mappings. Share security posture details with team leaders and CISOs."
    },
    {
      icon: <Cloud className="w-5 h-5" />,
      title: "Cloud Integrations",
      value: "Unified Operations",
      desc: "Connect AWS, GCP, and Azure accounts. Sync with Slack, PagerDuty, Splunk, or SIEM tools for real-time security alerts."
    }
  ];

  return (
    <section id="features" className="w-full py-24 relative z-10 overflow-hidden bg-[#FEF8E8]/40 border-y border-[#E8C4E3]/40">
      <div className="max-w-[1100px] mx-auto px-6">
        
        {/* Section Heading */}
        <div className="text-center mb-16">
          <div className="inline-flex items-center justify-center px-4 py-1.5 rounded-full text-[#9D288E] text-[13px] font-bold tracking-[0.04em] bg-[#F5E6F3] border border-[#E5C6E1] mb-4 shadow-2xs">
            PLATFORM MODULES
          </div>
          <h2 className="font-[family-name:var(--font-jakarta)] font-extrabold text-3xl md:text-5xl text-[#2A1B28] mb-4">
            Enterprise Security Architecture
          </h2>
          <p className="text-[#5A4B58] text-lg max-w-2xl mx-auto">
            A comprehensive suite of modules designed to deliver full visibility and control over cloud identity access.
          </p>
        </div>

        {/* Bento Grid */}
        <MotionDiv 
          variants={containerVariants}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, margin: "-100px" }}
          className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6"
        >
          {modules.map((m, idx) => (
            <InteractiveFeatureCard key={idx} m={m} idx={idx} />
          ))}
        </MotionDiv>
      </div>
    </section>
  );
}
