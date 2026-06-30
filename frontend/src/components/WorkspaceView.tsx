import React, { useState } from 'react';

interface Issue {
  id: string;
  audit_record_id: string;
  attribute: string;
  content_bucket: string;
  issue_type: string;
  root_cause: string | null;
  severity: string;
  confidence: string;
  regulatory_source: string | null;
  regulatory_section: string | null;
  current_content: string | null;
  suggested_content: string | null;
  evidence_text: string | null;
  reviewer_status: string;
  reviewer_comments: string | null;
  assigned_to: string | null;
  created_at: string;
}

interface WorkspaceViewProps {
  issues: Issue[];
  onUpdateIssue: (issueId: string, status: string, comments: string, assignee: string, severity: string, rootCause: string) => Promise<void>;
  loading: boolean;
}

export const WorkspaceView: React.FC<WorkspaceViewProps> = ({ issues, onUpdateIssue, loading }) => {
  const [selectedIssueId, setSelectedIssueId] = useState<string | null>(null);
  
  // Reviewer inputs
  const [status, setStatus] = useState<string>("Open");
  const [comments, setComments] = useState<string>("");
  const [assignee, setAssignee] = useState<string>("");
  const [severity, setSeverity] = useState<string>("Medium");
  const [rootCause, setRootCause] = useState<string>("Unknown");

  const selectedIssue = issues.find(i => i.id === selectedIssueId);

  const selectIssue = (issue: Issue) => {
    setSelectedIssueId(issue.id);
    setStatus(issue.reviewer_status);
    setComments(issue.reviewer_comments || "");
    setAssignee(issue.assigned_to || "");
    setSeverity(issue.severity);
    setRootCause(issue.root_cause || "Unknown");
  };

  const handleSave = async () => {
    if (selectedIssueId) {
      await onUpdateIssue(selectedIssueId, status, comments, assignee, severity, rootCause);
    }
  };

  const getSeverityColor = (sev: string) => {
    switch (sev) {
      case 'Critical': return '#ff007f'; // pink
      case 'High': return '#ff7b00'; // orange
      case 'Medium': return '#fee440'; // yellow
      default: return 'var(--accent-blue)';
    }
  };

  const getTypeLabel = (type: string) => {
    switch (type) {
      case 'INC': return 'Incorrect Content';
      case 'CON': return 'Contradictory/Inconsistent';
      case 'LCQ': return 'Low Quality Content';
      case 'MIS': return 'Missing Information';
      default: return type;
    }
  };

  return (
    <div style={{ display: 'flex', gap: '24px', height: 'calc(100vh - 180px)', minHeight: '500px' }}>
      
      {/* 1. Left List Panel */}
      <div className="glass-panel" style={{ width: '320px', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        <div style={{ padding: '16px', borderBottom: '1px solid rgba(255, 255, 255, 0.08)' }}>
          <h3 style={{ fontSize: '16px', fontWeight: '600' }}>Compliance Issues ({issues.length})</h3>
        </div>
        
        <div style={{ flex: '1', overflowY: 'auto', display: 'flex', flexDirection: 'column' }}>
          {issues.length === 0 ? (
            <div style={{ padding: '30px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '13px' }}>
              No issues detected. Run scraper and audits to audit pages.
            </div>
          ) : (
            issues.map((iss) => (
              <div 
                key={iss.id}
                onClick={() => selectIssue(iss)}
                style={{
                  padding: '16px',
                  borderBottom: '1px solid rgba(255, 255, 255, 0.05)',
                  cursor: 'pointer',
                  backgroundColor: selectedIssueId === iss.id ? 'rgba(0, 210, 255, 0.05)' : 'transparent',
                  borderLeft: selectedIssueId === iss.id ? '3px solid var(--accent-blue)' : 'none',
                  transition: 'all 0.2s ease'
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                  <span style={{
                    fontSize: '10px',
                    fontWeight: 'bold',
                    padding: '2px 6px',
                    borderRadius: '3px',
                    backgroundColor: 'rgba(255, 255, 255, 0.05)',
                    color: getSeverityColor(iss.severity)
                  }}>
                    {iss.severity}
                  </span>
                  <span style={{ fontSize: '10px', color: 'var(--text-secondary)' }}>{iss.reviewer_status}</span>
                </div>
                <h4 style={{ fontSize: '13px', fontWeight: '600', marginBottom: '4px' }}>{iss.attribute}</h4>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', color: 'var(--text-muted)' }}>
                  <span>{iss.content_bucket}</span>
                  <span style={{ fontWeight: 'bold' }}>{iss.issue_type}</span>
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {/* 2. Right Detail Panel */}
      <div className="glass-panel" style={{ flex: '1', display: 'flex', flexDirection: 'column', padding: '24px', overflowY: 'auto' }}>
        {!selectedIssue ? (
          <div style={{ flex: '1', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)', fontSize: '14px' }}>
            Select an issue from the sidebar to inspect medical compliance findings.
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            
            {/* Header */}
            <div style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.08)', paddingBottom: '16px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                <span style={{ color: 'var(--accent-blue)', fontSize: '12px', fontWeight: 'bold' }}>
                  {getTypeLabel(selectedIssue.issue_type)}
                </span>
                <span style={{ color: 'var(--text-muted)', fontSize: '11px' }}>ID: {selectedIssue.id}</span>
              </div>
              <h2 style={{ fontSize: '20px', fontWeight: '600' }}>Compliance Finding: {selectedIssue.attribute}</h2>
            </div>

            {/* Split Screen Layout */}
            <div style={{ display: 'flex', gap: '20px', flexWrap: 'wrap' }}>
              
              {/* Left Column: Front-End Content */}
              <div style={{ flex: '1', minWidth: '280px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
                <h4 style={{ fontSize: '14px', color: 'var(--text-secondary)' }}>Scraped Catalog Text</h4>
                <div style={{
                  padding: '16px',
                  borderRadius: '8px',
                  backgroundColor: 'rgba(255, 0, 127, 0.03)',
                  border: '1px solid rgba(255, 0, 127, 0.1)',
                  fontSize: '13px',
                  lineHeight: '1.6',
                  minHeight: '140px',
                  color: 'var(--text-primary)'
                }}>
                  {selectedIssue.current_content || (
                    <span style={{ color: 'var(--text-muted)', fontStyle: 'italic' }}>
                      [Omitted / Missing Attribute Section]
                    </span>
                  )}
                </div>
              </div>

              {/* Right Column: Regulatory Reference */}
              <div style={{ flex: '1', minWidth: '280px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
                <h4 style={{ fontSize: '14px', color: 'var(--text-secondary)' }}>
                  Retrieved Reference Citations ({selectedIssue.regulatory_source || "Tata 1mg Standard"})
                </h4>
                <div style={{
                  padding: '16px',
                  borderRadius: '8px',
                  backgroundColor: 'rgba(0, 245, 212, 0.03)',
                  border: '1px solid rgba(0, 245, 212, 0.1)',
                  fontSize: '13px',
                  lineHeight: '1.6',
                  minHeight: '140px',
                  color: 'var(--text-primary)'
                }}>
                  {selectedIssue.evidence_text || (
                    <span style={{ color: 'var(--text-muted)', fontStyle: 'italic' }}>
                      [Tata 1mg Editorial Standard checklist benchmark]
                    </span>
                  )}
                </div>
              </div>

            </div>

            {/* Suggested Update */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              <h4 style={{ fontSize: '14px', color: 'var(--text-secondary)' }}>Suggested Correction</h4>
              <div style={{
                padding: '16px',
                borderRadius: '8px',
                backgroundColor: 'rgba(255,255,255,0.02)',
                border: '1px solid rgba(255,255,255,0.05)',
                fontSize: '13px',
                lineHeight: '1.6',
                color: 'var(--status-success)'
              }}>
                {selectedIssue.suggested_content}
              </div>
            </div>

            {/* Audit Metadata info */}
            <div style={{
              display: 'flex',
              gap: '16px',
              padding: '16px',
              borderRadius: '8px',
              backgroundColor: 'var(--bg-secondary)',
              fontSize: '12px',
              flexWrap: 'wrap'
            }}>
              <div>
                <span style={{ color: 'var(--text-secondary)' }}>Confidence Level: </span>
                <span style={{ fontWeight: 'bold', color: 'var(--accent-blue)' }}>{selectedIssue.confidence}</span>
              </div>
              <div>
                <span style={{ color: 'var(--text-secondary)' }}>Issue Bucket: </span>
                <span style={{ fontWeight: 'bold' }}>{selectedIssue.content_bucket}</span>
              </div>
              <div>
                <span style={{ color: 'var(--text-secondary)' }}>Regulatory Source: </span>
                <span style={{ fontWeight: 'bold' }}>{selectedIssue.regulatory_source || "N/A"}</span>
              </div>
            </div>

            {/* Review Action Ticket Controls */}
            <div style={{
              borderTop: '1px solid rgba(255, 255, 255, 0.08)',
              paddingTop: '20px',
              display: 'flex',
              flexDirection: 'column',
              gap: '16px'
            }}>
              <h3 style={{ fontSize: '15px', fontWeight: '600' }}>Reviewer Workspace Decision</h3>
              
              <div style={{ display: 'flex', gap: '16px', flexWrap: 'wrap' }}>
                {/* Status selector */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', flex: '1', minWidth: '150px' }}>
                  <label style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>Workflow Status</label>
                  <select 
                    value={status} 
                    onChange={(e) => setStatus(e.target.value)}
                    style={{
                      padding: '8px',
                      borderRadius: '6px',
                      backgroundColor: 'var(--bg-secondary)',
                      border: '1px solid rgba(255,255,255,0.08)',
                      color: '#fff',
                      fontSize: '13px'
                    }}
                  >
                    {["Open", "Assigned", "Under Review", "Accepted", "Rejected", "Needs Discussion", "Resolved", "Revalidated", "Closed"].map(s => (
                      <option key={s} value={s}>{s}</option>
                    ))}
                  </select>
                </div>

                {/* Assignee */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', flex: '1', minWidth: '150px' }}>
                  <label style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>Assigned Owner</label>
                  <input 
                    type="text" 
                    value={assignee} 
                    onChange={(e) => setAssignee(e.target.value)}
                    placeholder="Enter owner name"
                    style={{
                      padding: '8px',
                      borderRadius: '6px',
                      backgroundColor: 'var(--bg-secondary)',
                      border: '1px solid rgba(255,255,255,0.08)',
                      color: '#fff',
                      fontSize: '13px'
                    }}
                  />
                </div>

                {/* Severity Adjuster */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', flex: '1', minWidth: '120px' }}>
                  <label style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>Change Severity</label>
                  <select 
                    value={severity} 
                    onChange={(e) => setSeverity(e.target.value)}
                    style={{
                      padding: '8px',
                      borderRadius: '6px',
                      backgroundColor: 'var(--bg-secondary)',
                      border: '1px solid rgba(255,255,255,0.08)',
                      color: '#fff',
                      fontSize: '13px'
                    }}
                  >
                    {["Critical", "High", "Medium", "Low", "Informational"].map(s => (
                      <option key={s} value={s}>{s}</option>
                    ))}
                  </select>
                </div>

                {/* Root Cause selector */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', flex: '1', minWidth: '150px' }}>
                  <label style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>Root Cause Classification</label>
                  <select 
                    value={rootCause} 
                    onChange={(e) => setRootCause(e.target.value)}
                    style={{
                      padding: '8px',
                      borderRadius: '6px',
                      backgroundColor: 'var(--bg-secondary)',
                      border: '1px solid rgba(255,255,255,0.08)',
                      color: '#fff',
                      fontSize: '13px'
                    }}
                  >
                    {["Regulatory Update", "Editorial Error", "Content Omission", "Mapping Error", "Legacy Content", "Taxonomy Error", "AI False Positive", "Unknown"].map(s => (
                      <option key={s} value={s}>{s}</option>
                    ))}
                  </select>
                </div>
              </div>

              {/* Reviewer Comments */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                <label style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>Audit / Reviewer Comments</label>
                <textarea 
                  value={comments}
                  onChange={(e) => setComments(e.target.value)}
                  placeholder="Enter comments about this compliance ticket..."
                  style={{
                    padding: '10px',
                    borderRadius: '6px',
                    backgroundColor: 'var(--bg-secondary)',
                    border: '1px solid rgba(255,255,255,0.08)',
                    color: '#fff',
                    fontSize: '13px',
                    minHeight: '80px',
                    resize: 'vertical'
                  }}
                />
              </div>

              {/* Save Button */}
              <button 
                onClick={handleSave}
                disabled={loading}
                style={{
                  alignSelf: 'flex-start',
                  padding: '10px 24px',
                  borderRadius: '8px',
                  border: 'none',
                  background: 'linear-gradient(135deg, var(--accent-blue) 0%, var(--accent-purple) 100%)',
                  color: '#fff',
                  fontWeight: '600',
                  cursor: loading ? 'not-allowed' : 'pointer',
                  opacity: loading ? 0.6 : 1
                }}
              >
                Submit Decision
              </button>

            </div>

          </div>
        )}
      </div>

    </div>
  );
};
