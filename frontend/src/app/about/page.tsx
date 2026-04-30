"use client";

import { motion } from "framer-motion";
import { Server, Activity, Network, Target, Cpu, GitMerge } from "lucide-react";

export default function AboutPage() {
  const containerVariants = {
    hidden: { opacity: 0 },
    visible: { opacity: 1, transition: { staggerChildren: 0.1 } },
  };

  const itemVariants = {
    hidden: { opacity: 0, y: 20 },
    visible: { opacity: 1, y: 0, transition: { type: "spring" as const, stiffness: 100 } },
  };

  return (
    <div className="min-h-[calc(100vh-64px)] bg-slate-950 flex flex-col items-center py-20 relative overflow-hidden">
      {/* Background Grid */}
      <div className="absolute inset-0 bg-[linear-gradient(to_right,#80808012_1px,transparent_1px),linear-gradient(to_bottom,#80808012_1px,transparent_1px)] bg-[size:24px_24px] pointer-events-none"></div>

      <motion.main 
        variants={containerVariants}
        initial="hidden"
        animate="visible"
        className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10 w-full"
      >
        <motion.div variants={itemVariants} className="text-center mb-16">
          <h1 className="text-4xl md:text-5xl font-extrabold tracking-tight text-white mb-6">
            Architecture & Vision
          </h1>
          <p className="text-lg text-slate-400 max-w-2xl mx-auto">
            KEEP v3 is a state-of-the-art multi-agent system built on LangGraph, utilizing deterministic routing and self-reflection to ensure hallucination-free outputs.
          </p>
        </motion.div>

        <div className="space-y-12">
          {/* Section 1 */}
          <motion.section variants={itemVariants} className="bg-slate-900/40 backdrop-blur-md border border-slate-800 rounded-3xl p-8 md:p-12 shadow-2xl relative overflow-hidden">
            <div className="absolute top-0 right-0 p-8 opacity-10">
              <Network className="w-48 h-48 text-blue-500" />
            </div>
            <div className="relative z-10">
               <div className="inline-flex items-center justify-center p-3 bg-blue-500/10 rounded-xl mb-6 border border-blue-500/20">
                  <Activity className="w-8 h-8 text-blue-400" />
               </div>
               <h2 className="text-2xl font-bold text-slate-200 mb-4">The LangGraph Pipeline</h2>
               <p className="text-slate-400 leading-relaxed mb-6">
                 Unlike traditional sequential LLM chains, KEEP v3 uses a cyclic graph architecture. The system can loop back upon itself—for example, if the Validator agent finds insufficient evidence, it can re-trigger the Search agent with refined parameters. This self-correction mimics human reasoning.
               </p>
               <ul className="space-y-3">
                 {[
                   "Deterministic state transitions defined by edge logic",
                   "In-memory checkpointing for streaming state to UI",
                   "Fault-tolerant execution with retries and fallbacks"
                 ].map((item, i) => (
                   <li key={i} className="flex items-center gap-3 text-slate-300">
                     <span className="flex-shrink-0 w-1.5 h-1.5 rounded-full bg-blue-500" />
                     {item}
                   </li>
                 ))}
               </ul>
            </div>
          </motion.section>

          {/* Grid Section */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <motion.div variants={itemVariants} className="bg-slate-900/40 border border-slate-800 rounded-3xl p-8 hover:bg-slate-800/40 transition-colors">
              <Server className="w-8 h-8 text-emerald-400 mb-4" />
              <h3 className="text-xl font-bold text-slate-200 mb-3">Hybrid RAG Search</h3>
              <p className="text-slate-400 text-sm leading-relaxed">
                We combine traditional vector search via Pinecone with direct SERP API access. When you upload a private document, it is semantically chunked and merged seamlessly with internet data context.
              </p>
            </motion.div>

            <motion.div variants={itemVariants} className="bg-slate-900/40 border border-slate-800 rounded-3xl p-8 hover:bg-slate-800/40 transition-colors">
              <Cpu className="w-8 h-8 text-purple-400 mb-4" />
              <h3 className="text-xl font-bold text-slate-200 mb-3">Cost-Efficient Routing</h3>
              <p className="text-slate-400 text-sm leading-relaxed">
                By classifying task complexity upfront, simple extraction and validation tasks are routed to local models like Llama-3, saving expensive Gemini/GPT-4o calls strictly for deep reasoning and synthesis.
              </p>
            </motion.div>
          </div>
          
          <motion.div variants={itemVariants} className="mt-12 text-center p-8 bg-gradient-to-r from-blue-900/20 via-indigo-900/20 to-purple-900/20 border border-indigo-500/20 rounded-3xl">
             <GitMerge className="w-10 h-10 text-indigo-400 mx-auto mb-4" />
             <h3 className="text-2xl font-bold text-white mb-2">Ready to explore?</h3>
             <p className="text-indigo-200 mb-6">See the multi-agent system in action right now.</p>
             <a href="/research" className="inline-block px-6 py-3 bg-indigo-500 hover:bg-indigo-600 text-white font-semibold rounded-xl transition-colors shadow-lg shadow-indigo-500/25">
               Try the Research Engine
             </a>
          </motion.div>
        </div>
      </motion.main>
    </div>
  );
}
