"use client";

import { useState, useRef, useEffect } from "react";

type AgentState = "idle" | "thinking" | "completed" | "error";

interface TraceNode {
  nodeName: string;
  timestamp: string;
  details?: any;
}

export default function Home() {
  const [query, setQuery] = useState("");
  const [openAiKey, setOpenAiKey] = useState("");
  const [isResearching, setIsResearching] = useState(false);
  const [agents, setAgents] = useState<{ [key: string]: AgentState }>({
    planner: "idle",
    search: "idle",
    validator: "idle",
    extractor: "idle",
    synthesizer: "idle",
    verifier: "idle",
    confidence: "idle",
  });
  const [trace, setTrace] = useState<TraceNode[]>([]);
  const [report, setReport] = useState<string>("");
  const [confidence, setConfidence] = useState<number>(0);
  const [validatedSources, setValidatedSources] = useState<any[]>([]);
  const [uploadedDocs, setUploadedDocs] = useState<any[]>([]);
  const [isUploading, setIsUploading] = useState(false);

  const bottomRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [trace]);

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files || e.target.files.length === 0) return;
    setIsUploading(true);
    
    const formData = new FormData();
    for (let i = 0; i < e.target.files.length; i++) {
      formData.append("files", e.target.files[i]);
    }
    
    try {
      const response = await fetch("http://localhost:8000/api/upload", {
        method: "POST",
        body: formData,
      });
      if (response.ok) {
        const data = await response.json();
        const successfulUploads = data.results.filter((r: any) => r.status === "success");
        setUploadedDocs(prev => [...prev, ...successfulUploads]);
      }
    } catch (err) {
      console.error("Upload failed", err);
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  const handleResearch = async () => {
    if (!query.trim()) return;
    setIsResearching(true);
    setReport("");
    setConfidence(0);
    setValidatedSources([]);
    setTrace([]);
    
    // Reset agent states
    setAgents({
      planner: "thinking",
      search: "idle",
      validator: "idle",
      extractor: "idle",
      synthesizer: "idle",
      verifier: "idle",
      confidence: "idle",
    });

    try {
      const response = await fetch("http://localhost:8000/api/research", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query, uploaded_docs: uploadedDocs.length > 0 ? uploadedDocs : undefined, openai_api_key: openAiKey || undefined }),
      });

      if (!response.body) throw new Error("No response body");

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        
        // SSE messages are separated by \n\n
        const parts = buffer.split("\n\n");
        buffer = parts.pop() || "";

        for (const part of parts) {
          if (part.startsWith("data: ")) {
            const dataStr = part.substring("data: ".length);
            try {
              const data = JSON.parse(dataStr);
              if (data.status === "completed") {
                setIsResearching(false);
                break;
              }
              if (data.error) {
                setTrace(t => [...t, { nodeName: "Error", timestamp: new Date().toLocaleTimeString(), details: data.error }]);
                setIsResearching(false);
                break;
              }

              if (data.node) {
                // Update agent state
                setAgents(prev => ({ ...prev, [data.node]: "completed" }));
                
                // Identify next agent to set to thinking
                const nodesOrder = ["planner", "search", "validator", "extractor", "synthesizer", "verifier", "confidence"];
                const currentIndex = nodesOrder.indexOf(data.node);
                if (currentIndex >= 0 && currentIndex < nodesOrder.length - 1) {
                   setAgents(prev => ({ ...prev, [nodesOrder[currentIndex + 1]]: "thinking" }));
                }

                // Add to trace
                setTrace(t => [...t, {
                  nodeName: data.node,
                  timestamp: new Date().toLocaleTimeString(),
                  details: data.state_update,
                }]);

                // Update final outputs if available
                if (data.state_update) {
                   if (data.state_update.final_report) setReport(data.state_update.final_report);
                   if (data.state_update.confidence) setConfidence(data.state_update.confidence);
                   if (data.state_update.validated_sources) setValidatedSources(data.state_update.validated_sources);
                }
              }
            } catch (e) {
              console.error("Error parsing JSON chunk", e);
            }
          }
        }
      }
    } catch (err: any) {
      console.error(err);
      setTrace(t => [...t, { nodeName: "Network Error", timestamp: new Date().toLocaleTimeString(), details: err.message }]);
    } finally {
      setIsResearching(false);
      setAgents(prev => {
        const reset: any = {};
        for (const key in prev) {
           reset[key] = prev[key] === "thinking" ? "idle" : prev[key];
        }
        return reset;
      });
    }
  };

  const getAgentColor = (state: AgentState) => {
    switch (state) {
      case "idle": return "bg-gray-800 text-gray-400 border-gray-700";
      case "thinking": return "bg-blue-900/40 text-blue-400 border-blue-500 animate-pulse ring-2 ring-blue-500/50";
      case "completed": return "bg-emerald-900/40 text-emerald-400 border-emerald-500";
      case "error": return "bg-red-900/40 text-red-400 border-red-500";
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-200 font-sans selection:bg-blue-500/30">
      <main className="max-w-6xl mx-auto p-6 lg:p-12">
        {/* Header */}
        <header className="mb-12 text-center space-y-4">
          <div className="inline-flex items-center gap-3 px-4 py-2 rounded-full bg-blue-500/10 text-blue-400 border border-blue-500/20 shadow-lg shadow-blue-500/5">
            <div className="w-2 h-2 rounded-full bg-blue-400 animate-pulse" />
            <span className="text-sm font-medium tracking-wide uppercase">Phase 1 Real-Time System</span>
          </div>
          <h1 className="text-5xl lg:text-6xl font-extrabold tracking-tight bg-gradient-to-r from-blue-400 via-indigo-400 to-purple-400 bg-clip-text text-transparent drop-shadow-sm">
            KEEP v3 Research
          </h1>
          <p className="text-lg text-slate-400 max-w-2xl mx-auto font-light">
            Enter a complex topic and watch the multi-agent system analyze, synthesize, and verify sources in real-time.
          </p>
        </header>

        {/* Document Upload Area */}
        <div className="max-w-3xl mx-auto mb-8 space-y-4">
          <div className="flex items-center justify-between bg-slate-900/50 backdrop-blur-md rounded-xl border border-slate-800 p-4">
            <div className="flex items-center gap-3">
              <span className="text-2xl">📄</span>
              <div>
                <h3 className="font-medium text-slate-200">Private Document Ingestion</h3>
                <p className="text-sm text-slate-400">Upload PDF, DOCX, CSV, or TXT for hybrid RAG search.</p>
              </div>
            </div>
            <div>
              <input 
                type="file" 
                multiple 
                className="hidden" 
                ref={fileInputRef}
                onChange={handleFileUpload}
                accept=".pdf,.docx,.csv,.txt,.md"
              />
              <button 
                onClick={() => fileInputRef.current?.click()}
                disabled={isUploading || isResearching}
                className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 text-sm font-medium rounded-lg border border-slate-700 transition-colors disabled:opacity-50 flex items-center gap-2"
              >
                {isUploading ? (
                  <><div className="w-4 h-4 border-2 border-slate-400 border-t-transparent rounded-full animate-spin"></div> Uploading...</>
                ) : (
                  <>+ Upload Files</>
                )}
              </button>
            </div>
          </div>
          
          {uploadedDocs.length > 0 && (
            <div className="flex flex-wrap gap-2">
              {uploadedDocs.map((doc, idx) => (
                <div key={idx} className="flex items-center gap-2 px-3 py-1.5 bg-emerald-900/20 text-emerald-400 border border-emerald-500/20 rounded-lg text-sm">
                  <span>✓</span>
                  <span className="truncate max-w-[200px]" title={doc.filename}>{doc.filename}</span>
                  <span className="text-emerald-500/50 text-xs">({doc.num_chunks} chunks)</span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Input Area */}
        <div className="max-w-3xl mx-auto mb-16 flex flex-col gap-4">
          <div className="relative">
            <div className="absolute inset-y-0 left-0 flex items-center pl-4 pointer-events-none">
              <span className="text-slate-500">🔑</span>
            </div>
            <input
              type="password"
              value={openAiKey}
              onChange={(e) => setOpenAiKey(e.target.value)}
              placeholder="Optional: Provide OpenAI API Key (defaults to backend environment)"
              className="w-full bg-slate-900/80 backdrop-blur-xl border border-slate-700/50 rounded-xl pl-11 pr-4 py-3 text-sm focus:outline-none focus:border-indigo-500/50 focus:ring-1 focus:ring-indigo-500/50 placeholder-slate-500 text-slate-200 transition-all shadow-inner"
              disabled={isResearching}
            />
          </div>

          <div className="relative group">
            <div className="absolute -inset-1 bg-gradient-to-r from-blue-500 via-indigo-500 to-purple-500 rounded-2xl blur opacity-25 group-hover:opacity-40 transition duration-500"></div>
            <div className="relative flex gap-2 p-2 bg-slate-900/80 backdrop-blur-xl rounded-2xl border border-slate-700/50 shadow-2xl">
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && !isResearching && handleResearch()}
              placeholder="E.g., What are the latest breakthroughs in solid-state batteries?"
              className="flex-1 bg-transparent px-6 py-4 text-lg focus:outline-none placeholder-slate-500"
              disabled={isResearching}
            />
            <button
              onClick={handleResearch}
              disabled={isResearching || !query.trim()}
              className="px-8 py-4 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white font-semibold rounded-xl transition-all shadow-lg shadow-blue-900/20 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
            >
              {isResearching ? (
                <>
                  <svg className="animate-spin h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>
                  Processing
                </>
              ) : "Research"}
            </button>
          </div>
        </div>
        </div>

        {/* Multi-Agent Pipeline Visualization */}
        <div className="mb-12">
          <h2 className="text-sm font-bold text-slate-500 uppercase tracking-widest mb-6 px-2">Pipeline Status</h2>
          <div className="flex flex-wrap justify-center gap-4">
            {Object.entries(agents).map(([name, state], idx) => (
              <div key={name} className="flex items-center gap-4">
                <div className={`
                  px-5 py-3 rounded-xl border font-medium flex items-center gap-3 transition-all duration-300 backdrop-blur-sm
                  ${getAgentColor(state)}
                `}>
                  {state === "thinking" && <div className="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin" />}
                  {state === "completed" && <span className="text-lg">✓</span>}
                  <span className="capitalize">{name}</span>
                </div>
                {idx < Object.keys(agents).length - 1 && (
                  <div className="hidden md:block w-8 h-px bg-slate-700" />
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Results Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          
          {/* Timeline & Trace */}
          <div className="lg:col-span-1 bg-slate-900/50 backdrop-blur-md rounded-2xl border border-slate-800 p-6 flex flex-col h-[600px]">
            <h3 className="text-xl font-semibold mb-6 flex items-center gap-2">
              <span className="text-blue-400">⚡</span> Live Trace
            </h3>
            <div className="flex-1 overflow-y-auto space-y-4 pr-2 custom-scrollbar">
              {trace.map((t, idx) => (
                <div key={idx} className="bg-slate-800/40 border border-slate-700/50 rounded-lg p-4 transition-all hover:bg-slate-800/60">
                  <div className="flex justify-between items-center mb-2">
                    <span className="font-medium text-blue-300 capitalize text-sm bg-blue-900/30 px-2 py-0.5 rounded">{t.nodeName}</span>
                    <span className="text-xs text-slate-500">{t.timestamp}</span>
                  </div>
                  {t.details?.sub_queries && t.nodeName === "planner" && (
                    <div className="text-sm text-slate-400 mt-2">
                      <p className="font-semibold text-slate-300 mb-1">Generated Sub-queries:</p>
                      <ul className="list-disc pl-4 space-y-1">
                        {t.details.sub_queries.map((sq: string, i: number) => <li key={i}>{sq}</li>)}
                      </ul>
                    </div>
                  )}
                  {t.nodeName === "search" && (
                     <div className="text-sm text-slate-400 mt-2">Found sources, ready for validation.</div>
                  )}
                </div>
              ))}
              {trace.length === 0 && !isResearching && (
                <div className="h-full flex items-center justify-center text-slate-600 text-sm">
                  Awaiting query to begin trace...
                </div>
              )}
              <div ref={bottomRef} />
            </div>
          </div>

          {/* Final Output */}
          <div className="lg:col-span-2 flex flex-col gap-8">
            {/* Report */}
            <div className="bg-slate-900/50 backdrop-blur-md rounded-2xl border border-slate-800 p-8 h-full min-h-[400px]">
              <div className="flex justify-between items-start mb-8">
                <h3 className="text-2xl font-bold flex items-center gap-3">
                  <span className="bg-gradient-to-br from-indigo-400 to-purple-400 bg-clip-text text-transparent">Synthesized Report</span>
                </h3>
                {confidence > 0 && (
                  <div className="text-right">
                    <div className="text-xs text-slate-400 uppercase tracking-wider mb-1 font-semibold">Confidence Score</div>
                    <div className={`text-3xl font-black ${confidence > 0.8 ? 'text-emerald-400' : confidence > 0.5 ? 'text-yellow-400' : 'text-red-400'}`}>
                      {(confidence * 100).toFixed(0)}%
                    </div>
                  </div>
                )}
              </div>
              
              {report ? (
                <div className="prose prose-invert prose-slate max-w-none prose-p:leading-relaxed prose-headings:text-slate-200">
                  {report.split('\n').map((line, i) => (
                    <p key={i} className="mb-4 text-slate-300">{line}</p>
                  ))}
                </div>
              ) : (
                <div className="h-full flex flex-col items-center justify-center text-slate-500 space-y-4">
                  {isResearching ? (
                    <>
                      <div className="w-12 h-12 border-4 border-slate-700 border-t-indigo-500 rounded-full animate-spin"></div>
                      <p className="animate-pulse">Synthesizing comprehensive analysis...</p>
                    </>
                  ) : (
                    <>
                      <svg className="w-16 h-16 opacity-20" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" /></svg>
                      <p>Final report will appear here</p>
                    </>
                  )}
                </div>
              )}
            </div>

            {/* Sources */}
            {validatedSources.length > 0 && (
              <div className="bg-slate-900/50 backdrop-blur-md rounded-2xl border border-slate-800 p-6">
                 <h3 className="text-lg font-semibold mb-4 text-slate-200 flex items-center gap-2">
                   <span className="text-emerald-400">📚</span> Validated Sources
                 </h3>
                 <div className="grid gap-3">
                   {validatedSources.map((src, i) => (
                     <a key={i} href={src.url} target="_blank" rel="noreferrer" className="flex items-center justify-between p-4 rounded-xl bg-slate-800/30 border border-slate-700/50 hover:bg-slate-800/80 hover:border-slate-600 transition-colors group">
                       <div className="truncate pr-4">
                         <div className="font-medium text-slate-200 group-hover:text-blue-400 transition-colors truncate">{src.title}</div>
                         <div className="text-xs text-slate-500 truncate mt-1">{src.url}</div>
                       </div>
                       <div className="shrink-0">
                         <span className="px-2.5 py-1 rounded text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                           Score: {src.final_score?.toFixed(2) || "N/A"}
                         </span>
                       </div>
                     </a>
                   ))}
                 </div>
              </div>
            )}
          </div>
        </div>
      </main>
      
      <style dangerouslySetInnerHTML={{__html: `
        .custom-scrollbar::-webkit-scrollbar { width: 6px; }
        .custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
        .custom-scrollbar::-webkit-scrollbar-thumb { background: #334155; border-radius: 10px; }
        .custom-scrollbar::-webkit-scrollbar-thumb:hover { background: #475569; }
      `}} />
    </div>
  );
}
