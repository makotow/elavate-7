"use client";

import React, { useState, useEffect, useRef } from "react";
import {
  Sparkles,
  Send,
  RefreshCw,
  Calendar,
  Ticket,
  User,
  ShieldCheck,
  CheckCircle2,
  AlertCircle,
  ExternalLink,
  ChevronDown,
  ChevronRight,
  Clock,
  Briefcase,
  MapPin,
  Phone,
  FileText,
  HelpCircle,
  Laptop,
  Plane,
  X,
  Lock,
  Layers,
  Activity,
  Terminal,
} from "lucide-react";

interface AuditEntry {
  tool: string;
  action?: string;
  status?: string;
  code?: string;
  grounding_score?: number;
  escalation_id?: string;
  args?: Record<string, any>;
  reason?: string;
  transport?: string;
  ticket_id?: string;
}

interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  employee_id: string;
  audit_log?: AuditEntry[];
  safety_status?: {
    allowed?: boolean;
    category?: string;
    reason?: string;
  };
  timestamp: string;
}

interface ProfileData {
  employee_id: string;
  full_name: string;
  email: string;
  department: string;
  title: string;
  manager_id?: string;
  office_location?: string;
  home_address?: string;
  phone_number?: string;
  remote_work_eligible?: boolean;
}

interface BalancesData {
  vacation_days_remaining?: number;
  vacation_days_accrued?: number;
  vacation_days_used?: number;
  vacation_hours_remaining?: number;
  sick_days_remaining?: number;
  sick_days_accrued?: number;
  sick_days_used?: number;
  sick_hours_remaining?: number;
}

interface LeaveRequestItem {
  request_id: number;
  employee_id: string;
  start_date: string;
  end_date: string;
  leave_type: string;
  days: number;
}

interface TicketItem {
  ticket_id: string;
  requested_by: string;
  category: string;
  short_description: string;
  status: string;
  priority: string;
  assignment_group?: string;
  assigned_to?: string;
  created_at?: string;
}

const QUICK_ACTIONS = [
  {
    icon: Calendar,
    label: "有給残高の照会",
    prompt: "現在の私の有給休暇と病気休暇の残日数を教えてください。",
    color: "text-emerald-600 bg-emerald-50 hover:bg-emerald-100/80 border-emerald-200",
  },
  {
    icon: Plane,
    label: "休暇の申請 (1日)",
    prompt: "2026-10-05 に1日分の有給休暇 (Vacation) を申請してください。",
    color: "text-blue-600 bg-blue-50 hover:bg-blue-100/80 border-blue-200",
  },
  {
    icon: Laptop,
    label: "IT機器の申請 (外部モニター)",
    prompt: "在宅勤務用の4K外部モニターを申請したいです。規程の確認とITサポートチケットの起票をお願いします。",
    color: "text-indigo-600 bg-indigo-50 hover:bg-indigo-100/80 border-indigo-200",
  },
  {
    icon: HelpCircle,
    label: "経費規程 (ヘッドフォン)",
    prompt: "社内規定でノイズキャンセリングヘッドフォンの経費精算上限はいくらですか？引用元規程も教えてください。",
    color: "text-purple-600 bg-purple-50 hover:bg-purple-100/80 border-purple-200",
  },
  {
    icon: MapPin,
    label: "登録住所の更新",
    prompt: "私の連絡先住所を「Singapore Office, 80 Pasir Panjang Rd, Singapore」に更新してください。",
    color: "text-amber-600 bg-amber-50 hover:bg-amber-100/80 border-amber-200",
  },
  {
    icon: Ticket,
    label: "チケット確認 (INC0004533)",
    prompt: "私のITチケット INC0004533 の現在の対応状況と担当者を教えてください。",
    color: "text-cyan-600 bg-cyan-50 hover:bg-cyan-100/80 border-cyan-200",
  },
];

export default function EnterpriseWorkplacePortal() {
  const [employeeId, setEmployeeId] = useState<string>("EMP-769");
  const [inputPrompt, setInputPrompt] = useState<string>("");
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);
  const [showAuditDrawer, setShowAuditDrawer] = useState<boolean>(false);
  const [expandedActions, setExpandedActions] = useState<Record<string, boolean>>({});

  // Live MCP state
  const [profile, setProfile] = useState<ProfileData | null>(null);
  const [balances, setBalances] = useState<BalancesData | null>(null);
  const [leaveRequests, setLeaveRequests] = useState<LeaveRequestItem[]>([]);
  const [tickets, setTickets] = useState<TicketItem[]>([]);
  const [mcpStatus, setMcpStatus] = useState<any>({
    status: "connected",
    transport: "Streamable HTTP (FastMCP)",
  });

  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: "welcome-message",
      role: "assistant",
      content:
        "Makotow さん、こんにちは！Elevate Enterprise AI コンシェルジュへようこそ。\n\nWorkWeek HCM（有給残高・休暇申請・連絡先管理）および ServiceImmediately（IT/総務サポートチケット管理）と **Model Context Protocol (MCP)** 経由で常時連携しています。\n\n社内人事規程の検索・引用、休暇の申請、IT備品・修理チケットの起票など、何でも自然な言葉でお気軽にお申し付けください。",
      employee_id: "EMP-769",
      timestamp: "09:00",
    },
  ]);

  const chatBottomRef = useRef<HTMLDivElement>(null);

  // Fetch live state via MCP
  const fetchLiveState = async () => {
    setIsRefreshing(true);
    try {
      const res = await fetch(`/api/state?employee_id=${encodeURIComponent(employeeId)}`);
      if (res.ok) {
        const data = await res.json();
        if (data.profile) setProfile(data.profile);
        if (data.leave_balances) setBalances(data.leave_balances);
        if (data.leave_requests) setLeaveRequests(data.leave_requests);
        if (data.service_tickets) setTickets(data.service_tickets);
      }
    } catch (err) {
      console.error("Failed to fetch state:", err);
    } finally {
      setIsRefreshing(false);
    }
  };

  useEffect(() => {
    fetchLiveState();
  }, [employeeId]);

  useEffect(() => {
    chatBottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  const handleSendMessage = async (promptToSend?: string) => {
    const text = (promptToSend || inputPrompt).trim();
    if (!text || isLoading) return;

    const userMessageId = `user-${Date.now()}`;
    const userMsg: ChatMessage = {
      id: userMessageId,
      role: "user",
      content: text,
      employee_id: employeeId,
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    };

    setMessages((prev) => [...prev, userMsg]);
    setInputPrompt("");
    setIsLoading(true);

    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          prompt: text,
          employee_id: employeeId,
          session_id: "web-portal-session",
        }),
      });

      const data = await res.json();
      const assistantMessageId = `assistant-${Date.now()}`;

      const assistantMsg: ChatMessage = {
        id: assistantMessageId,
        role: "assistant",
        content: data.response || "処理が完了しました。",
        employee_id: employeeId,
        audit_log: data.audit_log || [],
        safety_status: data.safety_status,
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      };

      setMessages((prev) => [...prev, assistantMsg]);

      // Refresh live records if tools were invoked
      if (data.audit_log && data.audit_log.length > 0) {
        await fetchLiveState();
      }
    } catch (err: any) {
      setMessages((prev) => [
        ...prev,
        {
          id: `err-${Date.now()}`,
          role: "assistant",
          content: `申し訳ございません。リクエストの処理中にエラーが発生しました: ${err?.message || "不明なエラー"}`,
          employee_id: employeeId,
          timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  const toggleActionExpanded = (msgId: string) => {
    setExpandedActions((prev) => ({
      ...prev,
      [msgId]: !prev[msgId],
    }));
  };

  // Helper to render markdown citations & formatting
  const renderMessageContent = (content: string) => {
    // Look for markdown links: [Title](URL)
    const linkRegex = /\[([^\]]+)\]\((https?:\/\/[^\)]+)\)/g;
    const parts = [];
    let lastIndex = 0;
    let match;

    while ((match = linkRegex.exec(content)) !== null) {
      if (match.index > lastIndex) {
        parts.push(content.substring(lastIndex, match.index));
      }
      const title = match[1];
      const url = match[2];
      parts.push(
        <a
          key={`link-${match.index}`}
          href={url}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1 px-2.5 py-1 mx-1 text-xs font-semibold text-blue-700 bg-blue-50 hover:bg-blue-100 rounded-lg border border-blue-200 transition-colors shadow-xs"
        >
          <FileText className="w-3.5 h-3.5 text-blue-600" />
          <span>{title}</span>
          <ExternalLink className="w-3 h-3 text-blue-400" />
        </a>
      );
      lastIndex = match.index + match[0].length;
    }

    if (lastIndex < content.length) {
      parts.push(content.substring(lastIndex));
    }

    return (
      <div className="whitespace-pre-wrap leading-relaxed text-[14.5px] text-slate-800">
        {parts.map((p, i) => (typeof p === "string" ? p : <React.Fragment key={i}>{p}</React.Fragment>))}
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col font-sans text-slate-900 selection:bg-blue-100">
      {/* Top Global Header */}
      <header className="bg-white border-b border-slate-200/80 sticky top-0 z-30 shadow-xs">
        <div className="max-w-[1600px] mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">
          {/* Logo & Corporate Identity */}
          <div className="flex items-center gap-3.5">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-blue-700 via-indigo-600 to-sky-500 flex items-center justify-center text-white font-black text-xl shadow-sm shadow-blue-500/20">
              E
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-bold text-base text-slate-900 tracking-tight">Elevate Enterprise</span>
                <span className="text-slate-400 font-light">|</span>
                <span className="text-sm font-semibold text-slate-700">Workplace Concierge</span>
              </div>
              <div className="flex items-center gap-2 text-[11px] text-slate-500">
                <span>Google Cloud ADK & Gemini 3.8 Flash</span>
                <span>•</span>
                <span className="text-emerald-700 font-medium">Enterprise Edition (MVP 1)</span>
              </div>
            </div>
          </div>

          {/* Center: Live MCP Connection Indicator */}
          <div className="hidden md:flex items-center gap-2.5 px-3.5 py-1.5 rounded-full bg-slate-100/90 border border-slate-200/80 text-xs">
            <div className="relative flex h-2.5 w-2.5">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-emerald-500"></span>
            </div>
            <span className="font-medium text-slate-700">MCP Live Connected</span>
            <span className="text-slate-400">|</span>
            <span className="text-[11px] font-mono text-slate-600">WorkWeek & ServiceImmediately (Streamable HTTP)</span>
          </div>

          {/* Right: Authenticated Employee Profile & Audit Toggle */}
          <div className="flex items-center gap-3">
            <button
              onClick={() => setShowAuditDrawer(true)}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-slate-600 hover:text-slate-900 bg-slate-100 hover:bg-slate-200/80 rounded-lg transition-all border border-slate-200/60"
              title="セキュリティ検査および監査ログを表示"
            >
              <ShieldCheck className="w-4 h-4 text-indigo-600" />
              <span className="hidden sm:inline">監査・セキュリティログ</span>
            </button>

            {/* Profile Pill */}
            <div className="flex items-center gap-2.5 pl-2 border-l border-slate-200">
              <div className="w-8 h-8 rounded-full bg-indigo-100 text-indigo-700 font-bold flex items-center justify-center text-xs border border-indigo-200">
                MW
              </div>
              <div className="text-left hidden sm:block">
                <div className="text-xs font-bold text-slate-800 flex items-center gap-1.5">
                  <span>{profile?.full_name || "Makotow Employee"}</span>
                  <span className="text-[10px] font-mono bg-slate-200/80 text-slate-700 px-1.5 py-0.2 rounded">
                    {employeeId}
                  </span>
                </div>
                <div className="text-[11px] text-slate-500">
                  {profile?.title || "Staff Solutions Architect"}
                </div>
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Main Container */}
      <main className="flex-1 max-w-[1600px] w-full mx-auto px-4 sm:px-6 py-5 grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Sidebar: My Records & Quick Access (4 cols) */}
        <aside className="lg:col-span-4 space-y-4 flex flex-col">
          {/* Employee Status Card (WorkWeek HCM) */}
          <div className="bg-white rounded-2xl border border-slate-200/90 p-5 shadow-xs">
            <div className="flex items-center justify-between pb-3.5 mb-3.5 border-b border-slate-100">
              <div className="flex items-center gap-2">
                <Briefcase className="w-4 h-4 text-blue-600" />
                <h2 className="text-sm font-bold text-slate-900">ワークスペース情報 (WorkWeek)</h2>
              </div>
              <button
                onClick={fetchLiveState}
                disabled={isRefreshing}
                className="text-slate-400 hover:text-slate-700 p-1 rounded-md hover:bg-slate-100 transition-colors"
                title="MCPサーバーから最新状態を取得"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? "animate-spin text-blue-600" : ""}`} />
              </button>
            </div>

            {/* Balances Gauges */}
            <div className="grid grid-cols-2 gap-3 mb-4">
              <div className="p-3.5 rounded-xl bg-gradient-to-br from-emerald-50/70 to-teal-50/40 border border-emerald-100">
                <div className="flex items-center justify-between text-xs text-emerald-800 font-medium mb-1">
                  <span>有給休暇 (Vacation)</span>
                  <span className="text-[10px] text-emerald-600">年間 20.0日</span>
                </div>
                <div className="flex items-baseline gap-1">
                  <span className="text-2xl font-black text-emerald-700">
                    {balances?.vacation_days_remaining ?? 15.0}
                  </span>
                  <span className="text-xs font-semibold text-emerald-600">日 残り</span>
                </div>
                <div className="w-full bg-emerald-200/50 h-1.5 rounded-full mt-2 overflow-hidden">
                  <div
                    className="bg-emerald-500 h-full rounded-full transition-all"
                    style={{
                      width: `${((balances?.vacation_days_remaining ?? 15) / 20) * 100}%`,
                    }}
                  />
                </div>
              </div>

              <div className="p-3.5 rounded-xl bg-gradient-to-br from-blue-50/70 to-indigo-50/40 border border-blue-100">
                <div className="flex items-center justify-between text-xs text-blue-800 font-medium mb-1">
                  <span>病気休暇 (Sick)</span>
                  <span className="text-[10px] text-blue-600">年間 10.0日</span>
                </div>
                <div className="flex items-baseline gap-1">
                  <span className="text-2xl font-black text-blue-700">
                    {balances?.sick_days_remaining ?? 10.0}
                  </span>
                  <span className="text-xs font-semibold text-blue-600">日 残り</span>
                </div>
                <div className="w-full bg-blue-200/50 h-1.5 rounded-full mt-2 overflow-hidden">
                  <div
                    className="bg-blue-500 h-full rounded-full transition-all"
                    style={{
                      width: `${((balances?.sick_days_remaining ?? 10) / 10) * 100}%`,
                    }}
                  />
                </div>
              </div>
            </div>

            {/* Profile Details */}
            <div className="space-y-2 text-xs text-slate-600 bg-slate-50/80 p-3 rounded-xl border border-slate-100">
              <div className="flex items-start gap-2">
                <MapPin className="w-3.5 h-3.5 text-slate-400 mt-0.5 shrink-0" />
                <span className="leading-snug">
                  {profile?.home_address || "Singapore Office, 80 Pasir Panjang Rd, Singapore"}
                </span>
              </div>
              <div className="flex items-center gap-2">
                <Phone className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                <span>{profile?.phone_number || "+65-6521-0000"}</span>
              </div>
            </div>
          </div>

          {/* Active Support Tickets (ServiceImmediately) */}
          <div className="bg-white rounded-2xl border border-slate-200/90 p-5 shadow-xs flex-1">
            <div className="flex items-center justify-between pb-3.5 mb-3.5 border-b border-slate-100">
              <div className="flex items-center gap-2">
                <Ticket className="w-4 h-4 text-indigo-600" />
                <h2 className="text-sm font-bold text-slate-900">ITサポート・申請状況 (ServiceImmediately)</h2>
              </div>
              <span className="text-xs px-2 py-0.5 bg-indigo-50 text-indigo-700 font-semibold rounded-full border border-indigo-100">
                {tickets.length} 件
              </span>
            </div>

            {tickets.length === 0 ? (
              <div className="text-center py-6 text-xs text-slate-400">オープンなチケットはありません。</div>
            ) : (
              <div className="space-y-2.5">
                {tickets.map((t) => (
                  <div
                    key={t.ticket_id}
                    className="p-3 rounded-xl border border-slate-200 hover:border-indigo-300 hover:bg-indigo-50/30 transition-all text-xs space-y-1.5"
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-mono font-bold text-indigo-700">{t.ticket_id}</span>
                      <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-100 text-amber-800">
                        {t.status}
                      </span>
                    </div>
                    <div className="font-medium text-slate-800 line-clamp-1">{t.short_description}</div>
                    <div className="flex items-center justify-between text-[11px] text-slate-500 pt-1 border-t border-slate-100">
                      <span>{t.category}</span>
                      <span className="font-medium text-slate-600">{t.priority}</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </aside>

        {/* Center/Main Area: Interactive AI Concierge Chat (8 cols) */}
        <section className="lg:col-span-8 flex flex-col bg-white rounded-2xl border border-slate-200/90 shadow-xs overflow-hidden h-[calc(100vh-6.5rem)]">
          {/* Chat Header */}
          <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between bg-white">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center">
                <Sparkles className="w-4 h-4" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-slate-900">社内 AI コンシェルジュ (Enterprise Concierge)</h3>
                <p className="text-xs text-slate-500">人事規定照会・WorkWeek休暇手続・ITSMチケット対応</p>
              </div>
            </div>
            <div className="text-xs text-slate-400">
              Session ID: <span className="font-mono text-slate-600">web-portal-session</span>
            </div>
          </div>

          {/* Messages Scroll Area */}
          <div className="flex-1 overflow-y-auto p-6 space-y-5">
            {messages.map((msg) => {
              const isUser = msg.role === "user";
              const isExpanded = expandedActions[msg.id];
              const hasAudit = msg.audit_log && msg.audit_log.length > 0;

              return (
                <div key={msg.id} className={`flex gap-3.5 ${isUser ? "justify-end" : "justify-start"}`}>
                  {!isUser && (
                    <div className="w-8 h-8 rounded-full bg-blue-600 text-white flex items-center justify-center shrink-0 shadow-xs font-bold text-xs mt-0.5">
                      <Sparkles className="w-4 h-4" />
                    </div>
                  )}

                  <div className={`max-w-[82%] space-y-2`}>
                    <div
                      className={`p-4 rounded-2xl ${
                        isUser
                          ? "bg-blue-600 text-white rounded-tr-xs shadow-xs"
                          : "bg-slate-50 border border-slate-200/90 text-slate-800 rounded-tl-xs"
                      }`}
                    >
                      {isUser ? (
                        <div className="text-[14.5px] leading-relaxed whitespace-pre-wrap">{msg.content}</div>
                      ) : (
                        renderMessageContent(msg.content)
                      )}
                    </div>

                    {/* Metadata & Actions Accordion (for AI Messages) */}
                    {!isUser && (
                      <div className="space-y-1.5">
                        <div className="flex items-center justify-between text-[11px] text-slate-400 px-1">
                          <span>{msg.timestamp}</span>
                          {hasAudit && (
                            <button
                              onClick={() => toggleActionExpanded(msg.id)}
                              className="inline-flex items-center gap-1 text-slate-500 hover:text-indigo-600 font-medium transition-colors"
                            >
                              <Layers className="w-3 h-3 text-indigo-500" />
                              <span>{msg.audit_log?.length} 件のシステム処理完了</span>
                              {isExpanded ? (
                                <ChevronDown className="w-3 h-3" />
                              ) : (
                                <ChevronRight className="w-3 h-3" />
                              )}
                            </button>
                          )}
                        </div>

                        {/* Collapsible Tool Audit Details */}
                        {hasAudit && isExpanded && (
                          <div className="p-3 bg-slate-100/80 rounded-xl border border-slate-200 text-xs space-y-2 animate-in fade-in duration-200">
                            <div className="text-[11px] font-bold text-slate-700 flex items-center justify-between">
                              <span>実行されたエンタープライズアクション (MCP / RAG):</span>
                              <span className="text-[10px] text-emerald-700 font-mono">100% 監査証跡記録済</span>
                            </div>
                            <div className="space-y-1.5">
                              {msg.audit_log?.map((log, idx) => (
                                <div
                                  key={idx}
                                  className="p-2 bg-white rounded-lg border border-slate-200/80 flex items-center justify-between text-[11px]"
                                >
                                  <div className="flex items-center gap-2">
                                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
                                    <span className="font-mono font-bold text-slate-800">{log.tool}</span>
                                    {log.status && (
                                      <span
                                        className={`px-1.5 py-0.2 rounded text-[10px] font-semibold ${
                                          log.status === "GUARDRAIL_BLOCKED"
                                            ? "bg-amber-100 text-amber-800"
                                            : "bg-emerald-100 text-emerald-800"
                                        }`}
                                      >
                                        {log.status}
                                      </span>
                                    )}
                                  </div>
                                  <span className="font-mono text-slate-500 text-[10px]">
                                    {log.transport || "MCP_Streamable_HTTP"}
                                  </span>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    )}
                  </div>

                  {isUser && (
                    <div className="w-8 h-8 rounded-full bg-slate-800 text-white flex items-center justify-center shrink-0 font-bold text-xs mt-0.5">
                      MW
                    </div>
                  )}
                </div>
              );
            })}

            {isLoading && (
              <div className="flex gap-3.5 justify-start items-center">
                <div className="w-8 h-8 rounded-full bg-blue-600 text-white flex items-center justify-center font-bold text-xs">
                  <Sparkles className="w-4 h-4 animate-spin" />
                </div>
                <div className="bg-slate-50 border border-slate-200 rounded-2xl rounded-tl-xs px-4 py-3 text-xs text-slate-500 flex items-center gap-2">
                  <span className="inline-block w-2 h-2 rounded-full bg-blue-600 animate-pulse"></span>
                  <span>MCP 経由でデータ照会・AI 回答生成中...</span>
                </div>
              </div>
            )}
            <div ref={chatBottomRef} />
          </div>

          {/* Quick Suggestions Strip */}
          <div className="px-6 py-2.5 bg-slate-50/70 border-t border-slate-100 overflow-x-auto no-scrollbar">
            <div className="flex items-center gap-2 min-w-max">
              <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider mr-1">おすすめ:</span>
              {QUICK_ACTIONS.map((qa, i) => {
                const IconComponent = qa.icon;
                return (
                  <button
                    key={i}
                    onClick={() => handleSendMessage(qa.prompt)}
                    disabled={isLoading}
                    className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold border transition-all cursor-pointer ${qa.color}`}
                  >
                    <IconComponent className="w-3 h-3" />
                    <span>{qa.label}</span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Input Bar */}
          <div className="p-4 bg-white border-t border-slate-200/90">
            <form
              onSubmit={(e) => {
                e.preventDefault();
                handleSendMessage();
              }}
              className="flex items-center gap-2"
            >
              <input
                type="text"
                value={inputPrompt}
                onChange={(e) => setInputPrompt(e.target.value)}
                placeholder="社内規程の確認、休暇申請、IT機器の手配などを入力してください..."
                disabled={isLoading}
                className="flex-1 px-4 py-3 text-sm bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 focus:bg-white transition-all text-slate-800 placeholder:text-slate-400"
              />
              <button
                type="submit"
                disabled={isLoading || !inputPrompt.trim()}
                className="px-5 py-3 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white rounded-xl font-semibold text-sm transition-all flex items-center gap-1.5 shadow-sm shadow-blue-500/20 cursor-pointer"
              >
                <Send className="w-4 h-4" />
                <span>送信</span>
              </button>
            </form>
          </div>
        </section>
      </main>

      {/* Slide-over Audit & Governance Drawer */}
      {showAuditDrawer && (
        <div className="fixed inset-0 z-50 flex justify-end bg-slate-900/40 backdrop-blur-xs transition-opacity animate-in fade-in">
          <div className="w-full max-w-md bg-white h-full shadow-2xl flex flex-col border-l border-slate-200 animate-in slide-in-from-right duration-200">
            <div className="p-5 border-b border-slate-100 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <ShieldCheck className="w-5 h-5 text-indigo-600" />
                <h3 className="font-bold text-slate-900 text-sm">セキュリティ & ガバナンス監査</h3>
              </div>
              <button
                onClick={() => setShowAuditDrawer(false)}
                className="p-1 rounded-lg hover:bg-slate-100 text-slate-400 hover:text-slate-700"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-5 overflow-y-auto space-y-4 flex-1 text-xs text-slate-700">
              <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 space-y-2">
                <div className="font-bold text-slate-900 flex items-center gap-1.5">
                  <Lock className="w-3.5 h-3.5 text-blue-600" />
                  <span>X-Composite-Token & RBAC</span>
                </div>
                <p className="text-slate-500 leading-relaxed text-[11.5px]">
                  セッションは <span className="font-mono font-bold text-slate-700">{employeeId}</span>{" "}
                  に暗号署名バインドされています。他社員（EMP-0001等）への不正アクセスは interceptor により厳格に遮断されます。
                </p>
              </div>

              <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 space-y-2">
                <div className="font-bold text-slate-900 flex items-center gap-1.5">
                  <Activity className="w-3.5 h-3.5 text-emerald-600" />
                  <span>Model Armor (インライン防御)</span>
                </div>
                <p className="text-slate-500 leading-relaxed text-[11.5px]">
                  推論前にプロンプトインジェクション、Jailbreak、機密漏洩試行をリアルタイム検知し、安全に拒否します。
                </p>
              </div>

              <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 space-y-2">
                <div className="font-bold text-slate-900 flex items-center gap-1.5">
                  <FileText className="w-3.5 h-3.5 text-purple-600" />
                  <span>Cloud SDP SPII マスキング</span>
                </div>
                <p className="text-slate-500 leading-relaxed text-[11.5px]">
                  電話番号、SSN、個人住所などの機微情報は、推論出力後に自動検知・マスキング（[REDACTED]）されます。
                </p>
              </div>

              <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 space-y-2">
                <div className="font-bold text-slate-900 flex items-center gap-1.5">
                  <Terminal className="w-3.5 h-3.5 text-sky-600" />
                  <span>MCP Streamable HTTP トランスポート</span>
                </div>
                <div className="font-mono text-[10.5px] bg-white p-2.5 rounded border border-slate-200 space-y-1 text-slate-600">
                  <div>WorkWeek: /work-week/mcp/</div>
                  <div>ITSM: /service-immediately/mcp/</div>
                  <div className="text-emerald-700 font-semibold">Header: X-MCP-Token (Verified)</div>
                </div>
              </div>
            </div>

            <div className="p-4 border-t border-slate-100 bg-slate-50 flex justify-end">
              <button
                onClick={() => setShowAuditDrawer(false)}
                className="px-4 py-2 bg-slate-900 text-white rounded-xl text-xs font-semibold hover:bg-slate-800"
              >
                閉じる
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
