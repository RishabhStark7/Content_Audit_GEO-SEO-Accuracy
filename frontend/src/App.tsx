import { useState, useEffect } from 'react';
import { DashboardView } from './components/DashboardView';
import { MedicinesView } from './components/MedicinesView';
import { WorkspaceView } from './components/WorkspaceView';

// API Configuration
const API_BASE = "http://127.0.0.1:8000/api/v1";

// Mock Fallback Data (renders gracefully if server is disconnected or bootloading)
const MOCK_SUMMARY = {
  total_urls: 5,
  urls_scraped: 5,
  urls_audited: 4,
  overall_medical_accuracy_score: 87.5,
  overall_completeness_score: 91.2,
  overall_content_health_score: 89.0,
  total_issues: 4,
  critical_issues: 0,
  high_issues: 1,
  medium_issues: 2,
  low_issues: 1,
  open_issues: 3,
  closed_issues: 1,
  average_resolution_time_hrs: 14.5
};

const MOCK_HEATMAP = {
  "Safety": 1,
  "FAQs": 0,
  "Metadata": 1,
  "Core Medical Content": 2,
  "Drug Interactions": 0
};

const MOCK_TRENDS = [
  { audit_id: "1", timestamp: "2026-06-01", accuracy: 80, completeness: 85, health: 82 },
  { audit_id: "2", timestamp: "2026-06-10", accuracy: 85, completeness: 90, health: 87 },
  { audit_id: "3", timestamp: "2026-06-20", accuracy: 85, completeness: 90, health: 87 },
  { audit_id: "4", timestamp: "2026-06-30", accuracy: 90, completeness: 95, health: 92 }
];

const MOCK_MEDICINES = [
  { id: 1, url: "https://www.1mg.com/drugs/dolo-650-tablet-74467", name: "Dolo 650 Tablet", generic_name: "Paracetamol (650mg)", priority: "High", owner: "Dr. Rohan", category: "Analgesic" }
];

const MOCK_AUDITS = [
  { id: "20260630-160039", medicine_id: 1, status: "Audited", completeness_score: 84.2, medical_accuracy_score: 70.0, content_health_score: 78.1, seo_score: 85, geo_score: 81, html_path: null, pdf_path: null, screenshot_path: null, json_path: null }
];

const MOCK_ISSUES = [
  {
    id: "iss-1",
    audit_record_id: "20260630-160039",
    attribute: "How it works",
    content_bucket: "Core Medical Content",
    issue_type: "MIS",
    root_cause: "Content Omission",
    severity: "High",
    confidence: "Very High",
    regulatory_source: "Tata 1mg Content Guideline",
    regulatory_section: null,
    current_content: null,
    suggested_content: "Add missing explanation of the therapeutic mechanism for Paracetamol.",
    evidence_text: "Dolo 650 Tablet is an analgesic (pain reliever) and antipyretic (fever reducer) which works by blocking chemical messengers.",
    reviewer_status: "Open",
    reviewer_comments: "Flagged during validator checks.",
    assigned_to: "Dr. Rohan",
    created_at: "2026-06-30T10:30:55"
  }
];

function App() {
  const [activeTab, setActiveTab] = useState<"DASHBOARD" | "MEDICINES" | "WORKSPACE">("DASHBOARD");
  const [loading, setLoading] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Live Database States
  const [summary, setSummary] = useState<any>(MOCK_SUMMARY);
  const [heatmap, setHeatmap] = useState<any>(MOCK_HEATMAP);
  const [trends, setTrends] = useState<any[]>(MOCK_TRENDS);
  const [medicines, setMedicines] = useState<any[]>(MOCK_MEDICINES);
  const [audits, setAudits] = useState<any[]>(MOCK_AUDITS);
  const [issues, setIssues] = useState<any[]>(MOCK_ISSUES);
  const [progress, setProgress] = useState<any>(null);

  const loadData = async () => {
    setLoading(true);
    setErrorMsg(null);
    try {
      // Parallel fetches with fallback
      const [sumRes, heatRes, trendRes, medRes, audRes, issRes, progRes] = await Promise.allSettled([
        fetch(`${API_BASE}/dashboard/summary`).then(r => r.json()),
        fetch(`${API_BASE}/dashboard/heatmap`).then(r => r.json()),
        fetch(`${API_BASE}/dashboard/trends`).then(r => r.json()),
        fetch(`${API_BASE}/scraper/list`).then(r => r.json()),
        fetch(`${API_BASE}/scraper/audits`).then(r => r.json()),
        fetch(`${API_BASE}/dashboard/issues`).then(r => r.json()),
        fetch(`${API_BASE}/dashboard/progress`).then(r => r.json())
      ]);

      if (sumRes.status === "fulfilled") setSummary(sumRes.value);
      if (heatRes.status === "fulfilled") setHeatmap(heatRes.value);
      if (trendRes.status === "fulfilled") setTrends(trendRes.value);
      if (medRes.status === "fulfilled") setMedicines(medRes.value);
      if (audRes.status === "fulfilled") setAudits(audRes.value);
      if (issRes.status === "fulfilled") setIssues(issRes.value);
      if (progRes.status === "fulfilled") setProgress(progRes.value);
      
    } catch (err: any) {
      console.warn("Could not connect to live backend API. Rendering default simulation sandbox.", err);
      setErrorMsg("Connected to sandbox mock database. Run local FastAPI backend to sync live catalog data.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    // Auto-refresh stats every 8 seconds
    const interval = setInterval(loadData, 8000);
    return () => clearInterval(interval);
  }, []);

  const handleUploadExcel = async (file: File) => {
    setLoading(true);
    try {
      const formData = new FormData();
      formData.append("file", file);
      
      const res = await fetch(`${API_BASE}/scraper/upload-excel`, {
        method: "POST",
        body: formData
      });
      if (res.ok) {
        await loadData();
      } else {
        throw new Error(await res.text());
      }
    } catch (err: any) {
      alert(`Excel upload failed: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleTriggerScrape = async (medId: number) => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/scraper/scrape-single?medicine_id=${medId}`, {
        method: "POST"
      });
      if (res.ok) {
        await loadData();
      } else {
        throw new Error(await res.text());
      }
    } catch (err: any) {
      alert(`Triggering scrape failed: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleTriggerAudit = async (auditId: string) => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/audit/trigger?audit_id=${auditId}`, {
        method: "POST"
      });
      if (res.ok) {
        await loadData();
      } else {
        throw new Error(await res.text());
      }
    } catch (err: any) {
      alert(`Triggering AI audit failed: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleUpdateIssue = async (
    issueId: string, 
    status: string, 
    comments: string, 
    assignee: string, 
    severity: string, 
    rootCause: string
  ) => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/dashboard/issues/${issueId}/update`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          reviewer_status: status,
          reviewer_comments: comments,
          assigned_to: assignee,
          severity: severity,
          root_cause: rootCause
        })
      });
      if (res.ok) {
        await loadData();
      } else {
        throw new Error(await res.text());
      }
    } catch (err: any) {
      // Local fallback for simulation if backend is off
      setIssues(prev => prev.map(iss => {
        if (iss.id === issueId) {
          return { ...iss, reviewer_status: status, reviewer_comments: comments, assigned_to: assignee, severity, root_cause: rootCause };
        }
        return iss;
      }));
      alert(`Update registered in sandbox! (Connect backend for DB sync).`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      
      {/* 1. Header Navigation */}
      <header style={{
        height: '70px',
        borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
        padding: '0 32px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        backgroundColor: 'var(--bg-secondary)',
        position: 'sticky',
        top: 0,
        zIndex: 100
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          {/* Glowing dot */}
          <div style={{ width: '10px', height: '10px', borderRadius: '50%', backgroundColor: 'var(--status-success)', boxShadow: '0 0 8px var(--status-success)' }} />
          <h1 style={{ fontSize: '20px', letterSpacing: '-0.03em' }}>
            Tata 1mg <span className="gradient-text">MCGP</span>
          </h1>
          <span style={{ fontSize: '11px', color: 'var(--text-muted)', borderLeft: '1px solid rgba(255,255,255,0.1)', paddingLeft: '12px', marginLeft: '4px' }}>
            Medical Content Governance Platform
          </span>
        </div>

        {/* Tab Selection */}
        <nav style={{ display: 'flex', gap: '16px' }}>
          {(["DASHBOARD", "MEDICINES", "WORKSPACE"] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              style={{
                background: 'transparent',
                border: 'none',
                color: activeTab === tab ? 'var(--text-primary)' : 'var(--text-secondary)',
                fontSize: '13px',
                fontWeight: '600',
                cursor: 'pointer',
                padding: '8px 16px',
                borderRadius: '6px',
                backgroundColor: activeTab === tab ? 'var(--bg-tertiary)' : 'transparent',
                transition: 'all 0.2s ease'
              }}
            >
              {tab.charAt(0) + tab.slice(1).toLowerCase()}
            </button>
          ))}
        </nav>
      </header>

      {/* 2. Main Dashboard Area */}
      <main style={{ flex: '1', padding: '32px', maxWidth: '1400px', width: '100%', margin: '0 auto' }}>
        
        {/* Real-time Progress Bar */}
        {progress && progress.pending > 0 && (
          <div style={{
            padding: '16px',
            backgroundColor: 'rgba(0, 210, 255, 0.04)',
            border: '1px solid rgba(0, 210, 255, 0.15)',
            borderRadius: '12px',
            marginBottom: '24px',
            display: 'flex',
            flexDirection: 'column',
            gap: '8px'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '13px' }}>
              <span style={{ fontWeight: '600' }}>🔄 Running Batch Content Audit...</span>
              <span style={{ color: 'var(--accent-blue)', fontWeight: 'bold' }}>
                {progress.completed} / {progress.total_skus} SKUs Done ({progress.percent_complete}%)
              </span>
            </div>
            <div style={{ width: '100%', height: '8px', backgroundColor: 'var(--bg-tertiary)', borderRadius: '4px', overflow: 'hidden' }}>
              <div style={{ width: `${progress.percent_complete}%`, height: '100%', background: 'linear-gradient(90deg, var(--accent-blue), var(--accent-purple))', transition: 'width 0.5s ease' }} />
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', color: 'var(--text-secondary)' }}>
              <span>Estimated Time Remaining: <strong>{progress.estimated_time_remaining}</strong></span>
              <span>Last Sync: {progress.last_updated}</span>
            </div>
          </div>
        )}

        {/* Warning notification banner if sandbox falls back */}
        {errorMsg && (
          <div style={{
            padding: '12px 24px',
            backgroundColor: 'rgba(0, 210, 255, 0.05)',
            border: '1px solid rgba(0, 210, 255, 0.15)',
            color: 'var(--accent-blue)',
            borderRadius: '8px',
            fontSize: '12px',
            marginBottom: '24px',
            display: 'flex',
            alignItems: 'center',
            gap: '8px'
          }}>
            <span>ℹ️</span> {errorMsg}
          </div>
        )}

        {/* Display Views */}
        {activeTab === "DASHBOARD" && (
          <DashboardView summary={summary} heatmap={heatmap} trends={trends} />
        )}
        {activeTab === "MEDICINES" && (
          <MedicinesView 
            medicines={medicines} 
            audits={audits}
            onUploadExcel={handleUploadExcel}
            onTriggerScrape={handleTriggerScrape}
            onTriggerAudit={handleTriggerAudit}
            loading={loading}
          />
        )}
        {activeTab === "WORKSPACE" && (
          <WorkspaceView 
            issues={issues} 
            onUpdateIssue={handleUpdateIssue} 
            loading={loading} 
          />
        )}

      </main>

      {/* 3. Footer */}
      <footer style={{
        padding: '20px 32px',
        borderTop: '1px solid rgba(255, 255, 255, 0.05)',
        textAlign: 'center',
        fontSize: '11px',
        color: 'var(--text-muted)',
        backgroundColor: '#05060a'
      }}>
        Tata 1mg Medical Affairs Content Governance Platform &copy; 2026. All rights reserved. Headless Playwright Auditor.
      </footer>

    </div>
  );
}

export default App;
