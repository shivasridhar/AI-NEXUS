"use client";

import Link from "next/link";
import { ShieldCheck, ChevronDown } from "lucide-react";
import { usePathname } from "next/navigation";

import { useState, useEffect } from "react";

export default function Navbar() {
  const [activeSection, setActiveSection] = useState(""); 

  const navLinks = [
    { name: "Features", href: "/#features" },
    { name: "How it Works", href: "/#how-it-works" },
    { name: "Pricing", href: "/#pricing" },
    { name: "FAQ", href: "/#faq" },
    { name: "Company", href: "/#company", hasDropdown: true }
  ];

  useEffect(() => {
    const handleScroll = () => {
      // Find the section that is currently in view
      let currentSection = "";
      
      for (const link of navLinks) {
        if (!link.href.includes('#')) continue;
        
        const sectionId = link.href.split('#')[1];
        const element = document.getElementById(sectionId);
        
        if (element) {
          const rect = element.getBoundingClientRect();
          const viewportCenter = window.innerHeight / 2;
          
          if (rect.top <= viewportCenter && rect.bottom >= viewportCenter) {
            currentSection = link.name;
            break;
          }
        }
      }
      setActiveSection(currentSection);
    };

    window.addEventListener("scroll", handleScroll);
    // Initial check
    handleScroll();
    
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  return (
    <nav className="fixed top-0 left-0 right-0 w-full flex items-center justify-between h-[72px] px-6 md:px-12 pt-4 z-50 bg-slate-50/80 backdrop-blur-md transition-all">
      
      {/* Left: Logo */}
      <Link href="/" className="flex items-center gap-2.5">
        <div className="w-8 h-8 rounded-lg bg-indigo-600 flex items-center justify-center">
          <ShieldCheck className="w-4.5 h-4.5 text-white" />
        </div>
        <span className="font-serif text-slate-900 font-bold text-[22px] tracking-tight">
          SentinelAI
        </span>
      </Link>

      {/* Center: Nav Pill */}
      <div className="hidden lg:flex items-center gap-1 bg-white rounded-full p-1.5 shadow-sm">
        {navLinks.map((item) => {
          const isActive = item.name === activeSection;
          
          return (
            <Link
              key={item.name}
              href={item.href}
              className={`
                flex items-center gap-1.5 px-4 py-2 rounded-full text-[15px] transition-all duration-200
                ${isActive 
                  ? "bg-white shadow-[0_2px_8px_rgba(54,15,60,0.08)] text-indigo-600 font-semibold" 
                  : "text-slate-600 font-normal hover:text-slate-900"}
              `}
            >
              {item.name}
              {item.hasDropdown && <ChevronDown className="w-3.5 h-3.5 opacity-60" />}
            </Link>
          );
        })}
      </div>

      {/* Right: CTA */}
      <div className="flex items-center gap-4">
        <Link
          href="/login"
          className="text-[15px] font-medium text-slate-600 hover:text-slate-900 transition-colors"
        >
          Log In
        </Link>
        <Link
          href="/signup"
          className="px-6 py-2.5 text-indigo-600 bg-transparent border-[1.5px] border-indigo-600 font-medium text-[15px] rounded-full hover:bg-indigo-50 transition-all"
        >
          Sign Up
        </Link>
      </div>

    </nav>
  );
}
