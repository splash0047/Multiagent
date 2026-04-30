"use client";

import { motion } from "framer-motion";
import Link from "next/link";
import { ArrowRight, Bot, Database, Zap, Lock, BarChart3, Search } from "lucide-react";

export default function LandingPage() {
  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: 0.1,
      },
    },
  };

  const itemVariants = {
    hidden: { opacity: 0, y: 20 },
    visible: { opacity: 1, y: 0, transition: { type: "spring" as const, stiffness: 100 } },
  };

  const features = [
    {
      title: "Real-Time AI Agents",
      description: "Watch as our specialized agents plan, search, validate, extract, and synthesize information interactively.",
      icon: <Bot className="w-6 h-6 text-blue-400" />,
      color: "from-blue-500/20 to-indigo-500/20"
    },
    {
      title: "Hybrid RAG Ingestion",
      description: "Upload your proprietary PDFs, DOCX, and CSVs. Our system seamlessly combines internal data with web search.",
      icon: <Lock className="w-6 h-6 text-emerald-400" />,
      color: "from-emerald-500/20 to-teal-500/20"
    },
    {
      title: "Persistent Memory",
      description: "Powered by Pinecone vector databases to retain insights and reduce redundant API calls over time.",
      icon: <Database className="w-6 h-6 text-purple-400" />,
      color: "from-purple-500/20 to-pink-500/20"
    },
    {
      title: "Smart Cost-Routing",
      description: "Dynamically routes complex logic to Gemini/GPT-4o and bulk processing to local Ollama Llama-3 models.",
      icon: <Zap className="w-6 h-6 text-amber-400" />,
      color: "from-amber-500/20 to-orange-500/20"
    },
  ];

  return (
    <div className="min-h-[calc(100vh-64px)] bg-slate-950 flex flex-col items-center justify-center overflow-hidden relative">
      {/* Background decorations */}
      <div className="absolute top-0 inset-x-0 h-96 bg-gradient-to-b from-blue-900/20 to-transparent pointer-events-none" />
      <div className="absolute -top-40 -right-40 w-96 h-96 bg-blue-500/10 blur-[100px] rounded-full pointer-events-none" />
      <div className="absolute -bottom-40 -left-40 w-96 h-96 bg-purple-500/10 blur-[100px] rounded-full pointer-events-none" />

      <motion.main 
        variants={containerVariants}
        initial="hidden"
        animate="visible"
        className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20 lg:py-32 relative z-10 w-full"
      >
        <div className="text-center max-w-4xl mx-auto mb-20">
          <motion.div variants={itemVariants} className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-slate-900/50 border border-slate-800 text-slate-300 text-sm mb-6 backdrop-blur-md">
            <span className="flex h-2 w-2 relative">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-blue-500"></span>
            </span>
            KEEP v3 is now live with real-time tracking
          </motion.div>

          <motion.h1 variants={itemVariants} className="text-5xl md:text-7xl font-extrabold tracking-tight text-white mb-8">
            The World's Most Transparent <br className="hidden md:block" />
            <span className="bg-gradient-to-r from-blue-400 via-indigo-400 to-purple-400 text-transparent bg-clip-text">
              Multi-Agent Engine
            </span>
          </motion.h1>

          <motion.p variants={itemVariants} className="text-xl text-slate-400 mb-10 max-w-2xl mx-auto font-light leading-relaxed">
            Unleash the power of interconnected AI. KEEP v3 orchestrates multiple specialized agents to research, validate, and synthesize actionable intelligence in seconds.
          </motion.p>

          <motion.div variants={itemVariants} className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <Link href="/research">
              <button className="group relative px-8 py-4 bg-white text-slate-950 font-bold rounded-full overflow-hidden transition-all hover:scale-105 active:scale-95 flex items-center gap-2">
                <span className="relative z-10">Launch Research Engine</span>
                <ArrowRight className="w-5 h-5 relative z-10 group-hover:translate-x-1 transition-transform" />
                <div className="absolute inset-0 bg-gradient-to-r from-slate-100 to-slate-300 opacity-0 group-hover:opacity-100 transition-opacity" />
              </button>
            </Link>
            <Link href="/about">
              <button className="px-8 py-4 bg-slate-900 text-white font-medium rounded-full border border-slate-800 hover:bg-slate-800 hover:border-slate-700 transition-all flex items-center gap-2">
                <Search className="w-5 h-5 text-slate-400" />
                Learn How It Works
              </button>
            </Link>
          </motion.div>
        </div>

        {/* Feature Grid */}
        <motion.div variants={itemVariants} className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {features.map((feature, idx) => (
            <div 
              key={idx}
              className="relative group p-6 bg-slate-900/50 backdrop-blur-sm border border-slate-800 rounded-2xl hover:bg-slate-800/50 transition-colors"
            >
              <div className={`absolute inset-0 bg-gradient-to-br ${feature.color} opacity-0 group-hover:opacity-10 rounded-2xl transition-opacity`} />
              <div className="w-12 h-12 rounded-xl bg-slate-950 border border-slate-800 flex items-center justify-center mb-6 shadow-inner">
                {feature.icon}
              </div>
              <h3 className="text-lg font-bold text-slate-200 mb-3">{feature.title}</h3>
              <p className="text-slate-400 text-sm leading-relaxed">{feature.description}</p>
            </div>
          ))}
        </motion.div>
      </motion.main>
    </div>
  );
}
