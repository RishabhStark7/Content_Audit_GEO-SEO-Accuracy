import React, { useState } from 'react';

interface SummaryData {
  total_urls: number;
  urls_scraped: number;
  urls_audited: number;
  overall_medical_accuracy_score: number;
  overall_completeness_score: number;
  overall_content_health_score: number;
  total_issues: number;
  critical_issues: number;
  high_issues: number;
  medium_issues: number;
  low_issues: number;
  open_issues: number;
  closed_issues: number;
  average_resolution_time_hrs: number;
}

interface TrendPoint {
  audit_id: string;
  timestamp: string;
  accuracy: number;
  completeness: number;
  health: number;
}

interface IssueData {
  id: string;
  audit_record_id: string;
  attribute: string;
  content_bucket: string;
  issue_type: string; // "MIS", "INC", "CON", "LCQ"
  severity: string; // "Critical", "High", "Medium", "Low"
  suggested_content: string | null;
  reviewer_status: string;
}

interface MedicineData {
  id: number;
  url: string;
  name: string;
  generic_name?: string;
}

interface AuditData {
  id: string;
  medicine_id: number;
  status: string;
}

interface DashboardViewProps {
  summary: SummaryData;
  heatmap: Record<string, number>;
  trends: TrendPoint[];
  issues: IssueData[];
  medicines: MedicineData[];
  audits: AuditData[];
}

export const DashboardView: React.FC<DashboardViewProps> = ({ 
  summary, 
  heatmap, 
  trends,
  issues,
  medicines,
  audits
}) => {
  // Modal State
  const [selectedBucket, setSelectedBucket] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [severityFilter, setSeverityFilter] = useState<string>('ALL');
  const [typeFilter, setTypeFilter] = useState<string>('ALL');

  // Score circle rendering helper (Google Sans-style expanded and highly readable donut)
  const renderScoreCircle = (score: number, title: string, subtitle: string, color: string) => {
    const radius = 62;
    const strokeWidth = 6;
    const circumference = 2 * Math.PI * radius;
    const offset = circumference - (score / 100) * circumference;

    return (
      <div className="glass-panel" style={{ padding: '24px', display: 'flex', flexDirection: 'column', alignItems: 'center', flex: '1', minWidth: '240px', backgroundColor: 'var(--bg-secondary)', border: '1px solid #dadce0', borderRadius: '8px' }}>
        <div style={{ position: 'relative', width: '150px', height: '150px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <svg style={{ transform: 'rotate(-90deg)', width: '150px', height: '150px' }}>
            <circle cx="75" cy="75" r={radius} fill="transparent" stroke="#f1f3f4" strokeWidth={strokeWidth} />
            <circle cx="75" cy="75" r={radius} fill="transparent" stroke={color} strokeWidth={strokeWidth} strokeDasharray={circumference} strokeDashoffset={offset} strokeLinecap="round" style={{ transition: 'stroke-dashoffset 0.6s cubic-bezier(0.4, 0, 0.2, 1)' }} />
          </svg>
          <div style={{ position: 'absolute', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
            <span style={{ fontSize: '22px', fontWeight: '500', fontFamily: 'var(--font-display)', color: 'var(--text-primary)', lineHeight: '1.1' }}>{score}%</span>
            <span style={{ fontSize: '11px', color: 'var(--text-secondary)', fontWeight: '400', marginTop: '4px' }}>{subtitle}</span>
          </div>
        </div>
        <h3 style={{ marginTop: '20px', fontSize: '15px', fontWeight: '500', color: 'var(--text-primary)', fontFamily: 'var(--font-display)' }}>{title}</h3>
      </div>
    );
  };

  // SVG Trend Chart with Shaded Area Gradients (Google Analytics Style)
  const renderTrendChart = () => {
    if (!trends || trends.length === 0) {
      return (
        <div style={{ height: '200px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)' }}>
          No historical trend data available.
        </div>
      );
    }

    const width = 600;
    const height = 240;
    const padding = 40;
    const pointsCount = trends.length;
    
    // Scale helper
    const getX = (idx: number) => padding + (idx / (pointsCount - 1 || 1)) * (width - 2 * padding);
    const getY = (val: number) => height - padding - (val / 100) * (height - 2 * padding);

    // Build SVG path lines
    let accuracyPath = "";
    let completenessPath = "";
    let healthPath = "";

    trends.forEach((pt, idx) => {
      const x = getX(idx);
      const yAcc = getY(pt.accuracy);
      const yComp = getY(pt.completeness);
      const yHealth = getY(pt.health);

      if (idx === 0) {
        accuracyPath = `M ${x} ${yAcc}`;
        completenessPath = `M ${x} ${yComp}`;
        healthPath = `M ${x} ${yHealth}`;
      } else {
        accuracyPath += ` L ${x} ${yAcc}`;
        completenessPath += ` L ${x} ${yComp}`;
        healthPath += ` L ${x} ${yHealth}`;
      }
    });

    // Close the area paths under the line to construct shade regions
    let healthAreaPath = "";
    let completenessAreaPath = "";
    if (pointsCount > 0) {
      const firstX = getX(0);
      const lastX = getX(pointsCount - 1);
      const yBottom = height - padding;
      
      healthAreaPath = `${healthPath} L ${lastX} ${yBottom} L ${firstX} ${yBottom} Z`;
      completenessAreaPath = `${completenessPath} L ${lastX} ${yBottom} L ${firstX} ${yBottom} Z`;
    }

    return (
      <svg viewBox={`0 0 ${width} ${height}`} style={{ width: '100%', height: 'auto', maxHeight: '280px' }}>
        {/* Define gradients for fill regions */}
        <defs>
          <linearGradient id="healthGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="var(--status-success)" stopOpacity="0.18" />
            <stop offset="100%" stopColor="var(--status-success)" stopOpacity="0.0" />
          </linearGradient>
          <linearGradient id="completenessGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="var(--accent-purple)" stopOpacity="0.12" />
            <stop offset="100%" stopColor="var(--accent-purple)" stopOpacity="0.0" />
          </linearGradient>
        </defs>

        {/* Y Axis gridlines */}
        {[0, 25, 50, 75, 100].map((gridVal) => {
          const y = getY(gridVal);
          return (
            <g key={gridVal}>
              <line x1={padding} y1={y} x2={width - padding} y2={y} stroke="#f1f3f4" strokeWidth="1" />
              <text x={padding - 10} y={y + 4} fill="var(--text-muted)" fontSize="10" textAnchor="end">{gridVal}</text>
            </g>
          );
        })}
        
        {/* Render Shaded Area Gradients underneath line strokes */}
        {healthAreaPath && <path d={healthAreaPath} fill="url(#healthGrad)" />}
        {completenessAreaPath && <path d={completenessAreaPath} fill="url(#completenessGrad)" />}
        
        {/* Render path strokes */}
        <path d={accuracyPath} fill="transparent" stroke="var(--accent-blue)" strokeWidth="2" strokeLinecap="round" />
        <path d={completenessPath} fill="transparent" stroke="var(--accent-purple)" strokeWidth="2" strokeLinecap="round" />
        <path d={healthPath} fill="transparent" stroke="var(--status-success)" strokeWidth="3" strokeLinecap="round" />
        
        {/* Render interactive coordinate nodes */}
        {trends.map((pt, idx) => (
          <circle key={idx} cx={getX(idx)} cy={getY(pt.health)} r="3.5" fill="var(--status-success)" stroke="#ffffff" strokeWidth="1.5" />
        ))}
      </svg>
    );
  };

  // Get color for density cell (light theme Google palette shades)
  const getDensityColor = (count: number) => {
    if (count === 0) return '#e6f4ea'; // Light green
    if (count < 3) return '#fef7e0'; // Light yellow
    if (count < 6) return '#fce8e6'; // Light red/pink
    return '#f9d2ce'; // Deeper light red
  };

  // Helper to map issue to medicine
  const getMedicineForIssue = (auditRecordId: string) => {
    const audit = audits.find(a => a.id === auditRecordId);
    if (!audit) return { id: 0, name: "Unknown SKU", url: "" };
    const med = medicines.find(m => m.id === audit.medicine_id);
    return med || { id: audit.medicine_id, name: `SKU #${audit.medicine_id}`, url: "" };
  };

  // Filter issues for active category modal
  const getFilteredIssues = () => {
    if (!selectedBucket) return [];
    
    return issues.filter(iss => {
      if (iss.content_bucket !== selectedBucket) return false;
      
      const med = getMedicineForIssue(iss.audit_record_id);
      
      // Name Search query filter
      if (searchQuery && !med.name.toLowerCase().includes(searchQuery.toLowerCase())) {
        return false;
      }
      
      // Severity filter
      if (severityFilter !== 'ALL' && iss.severity !== severityFilter) {
        return false;
      }
      
      // Domain Type filter
      if (typeFilter !== 'ALL') {
        const isCompleteness = iss.issue_type === 'MIS';
        if (typeFilter === 'COMPLETENESS' && !isCompleteness) return false;
        if (typeFilter === 'ACCURACY' && isCompleteness) return false;
      }
      
      return true;
    });
  };

  // Sort issues descending by severity weight (Critical -> High -> Medium -> Low)
  const getSortedIssues = () => {
    const list = getFilteredIssues();
    const severityWeight: Record<string, number> = {
      "Critical": 4,
      "High": 3,
      "Medium": 2,
      "Low": 1
    };
    
    return list.sort((a, b) => {
      const wA = severityWeight[a.severity] || 0;
      const wB = severityWeight[b.severity] || 0;
      return wB - wA;
    });
  };

  const activeIssues = getSortedIssues();

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      
      {/* 1. Score Summary Row */}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '24px' }}>
        {renderScoreCircle(summary.overall_content_health_score, "Content Health Score", "Weighted", "var(--status-success)")}
        {renderScoreCircle(summary.overall_medical_accuracy_score, "Medical Accuracy Score", "AI-Audited", "var(--accent-blue)")}
        {renderScoreCircle(summary.overall_completeness_score, "Completeness Score", "Completeness", "var(--accent-purple)")}
      </div>

      {/* 2. Operational KPIs Row */}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '24px' }}>
        {/* Core numbers */}
        <div className="glass-panel" style={{ padding: '24px', flex: '1.2', minWidth: '280px', display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '20px', backgroundColor: 'var(--bg-secondary)', border: '1px solid #dadce0' }}>
          <div>
            <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>Total Registered SKU</div>
            <div style={{ fontSize: '32px', fontWeight: '500', marginTop: '4px', color: 'var(--text-primary)', fontFamily: 'var(--font-display)' }}>{summary.total_urls}</div>
          </div>
          <div>
            <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>Completed Scrapes</div>
            <div style={{ fontSize: '32px', fontWeight: '500', marginTop: '4px', color: 'var(--accent-blue)', fontFamily: 'var(--font-display)' }}>{summary.urls_scraped}</div>
          </div>
          <div>
            <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>Total Audit Cases</div>
            <div style={{ fontSize: '32px', fontWeight: '500', marginTop: '4px', color: 'var(--accent-purple)', fontFamily: 'var(--font-display)' }}>{summary.urls_audited}</div>
          </div>
          <div>
            <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>Active Open Issues</div>
            <div style={{ fontSize: '32px', fontWeight: '500', marginTop: '4px', color: 'var(--status-danger)', fontFamily: 'var(--font-display)' }}>{summary.open_issues}</div>
          </div>
        </div>

        {/* Severity list (Minimalist clean lines, solid color bullets with no border) */}
        <div className="glass-panel" style={{ padding: '24px', flex: '1', minWidth: '280px', backgroundColor: 'var(--bg-secondary)', border: '1px solid #dadce0' }}>
          <h3 style={{ fontSize: '16px', marginBottom: '16px', fontWeight: '500', color: 'var(--text-primary)', fontFamily: 'var(--font-display)' }}>Compliance Issues by Severity</h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
            
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '8px 0', borderBottom: '1px solid #f1f3f4' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <span style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: 'var(--status-danger)', display: 'inline-block' }} />
                <span style={{ fontSize: '13px', color: 'var(--text-primary)', fontWeight: '400' }}>Critical Issues</span>
              </div>
              <span style={{ fontSize: '14px', fontWeight: '600', color: 'var(--text-primary)' }}>{summary.critical_issues}</span>
            </div>
            
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '8px 0', borderBottom: '1px solid #f1f3f4' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <span style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: 'var(--status-warning)', display: 'inline-block' }} />
                <span style={{ fontSize: '13px', color: 'var(--text-primary)', fontWeight: '400' }}>High Issues</span>
              </div>
              <span style={{ fontSize: '14px', fontWeight: '600', color: 'var(--text-primary)' }}>{summary.high_issues}</span>
            </div>
            
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '8px 0', borderBottom: '1px solid #f1f3f4' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <span style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: '#f9ab00', display: 'inline-block' }} />
                <span style={{ fontSize: '13px', color: 'var(--text-primary)', fontWeight: '400' }}>Medium Issues</span>
              </div>
              <span style={{ fontSize: '14px', fontWeight: '600', color: 'var(--text-primary)' }}>{summary.medium_issues}</span>
            </div>
            
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '8px 0' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <span style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: 'var(--accent-blue)', display: 'inline-block' }} />
                <span style={{ fontSize: '13px', color: 'var(--text-primary)', fontWeight: '400' }}>Low Issues</span>
              </div>
              <span style={{ fontSize: '14px', fontWeight: '600', color: 'var(--text-primary)' }}>{summary.low_issues}</span>
            </div>
            
          </div>
        </div>
      </div>

      {/* 3. Deep visual metrics (Heatmap + Trends) */}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '24px' }}>
        
        {/* Historical Trends chart */}
        <div className="glass-panel" style={{ padding: '24px', flex: '2', minWidth: '350px', backgroundColor: 'var(--bg-secondary)', border: '1px solid #dadce0' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
            <h3 style={{ fontSize: '16px', fontWeight: '500', color: 'var(--text-primary)', fontFamily: 'var(--font-display)' }}>Governance Trend Analysis</h3>
            <div style={{ display: 'flex', gap: '12px', fontSize: '11px' }}>
              <span style={{ color: 'var(--status-success)' }}>● Health</span>
              <span style={{ color: 'var(--accent-blue)' }}>● Accuracy</span>
              <span style={{ color: 'var(--accent-purple)' }}>● Completeness</span>
            </div>
          </div>
          {renderTrendChart()}
        </div>

        {/* Heatmap density grid */}
        <div className="glass-panel" style={{ padding: '24px', flex: '1.2', minWidth: '280px', backgroundColor: 'var(--bg-secondary)', border: '1px solid #dadce0' }}>
          <h3 style={{ fontSize: '16px', fontWeight: '500', marginBottom: '4px', color: 'var(--text-primary)', fontFamily: 'var(--font-display)' }}>Compliance Risk Heatmap</h3>
          <p style={{ fontSize: '11px', color: 'var(--text-secondary)', marginBottom: '16px' }}>Click category cell to review active issues list</p>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '12px' }}>
            {['Safety', 'FAQs', 'Metadata', 'Core Medical Content', 'Drug Interactions'].map((bucket) => {
              const count = heatmap[bucket] || 0;
              return (
                <div 
                  key={bucket} 
                  onClick={() => {
                    setSelectedBucket(bucket);
                    setSearchQuery('');
                    setSeverityFilter('ALL');
                    setTypeFilter('ALL');
                  }}
                  style={{
                    padding: '16px', 
                    borderRadius: '8px', 
                    backgroundColor: getDensityColor(count),
                    border: '1px solid #dadce0',
                    display: 'flex',
                    flexDirection: 'column',
                    justifyContent: 'space-between',
                    minHeight: '90px',
                    cursor: 'pointer',
                    transform: 'scale(1)',
                    transition: 'all 0.15s ease-in-out'
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.transform = 'scale(1.02)';
                    e.currentTarget.style.boxShadow = '0 2px 5px rgba(0,0,0,0.05)';
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.transform = 'scale(1)';
                    e.currentTarget.style.boxShadow = 'none';
                  }}
                >
                  <span style={{ fontSize: '12px', color: '#202124', fontWeight: '500' }}>{bucket}</span>
                  <span style={{ fontSize: '20px', fontWeight: '500', marginTop: '8px', color: '#202124', fontFamily: 'var(--font-display)' }}>
                    {count} {count === 1 ? 'Issue' : 'Issues'}
                  </span>
                </div>
              );
            })}
          </div>
        </div>

      </div>

      {/* 4. Interactive Compliance List Modal Overlay */}
      {selectedBucket && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          width: '100vw',
          height: '100vh',
          backgroundColor: 'rgba(32, 33, 36, 0.4)',
          backdropFilter: 'blur(3px)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 1000,
          animation: 'fadeIn 0.2s ease-out'
        }}>
          <div style={{
            backgroundColor: '#ffffff',
            borderRadius: '8px',
            width: '90%',
            maxWidth: '850px',
            maxHeight: '85vh',
            padding: '24px',
            display: 'flex',
            flexDirection: 'column',
            boxShadow: '0 4px 16px rgba(0,0,0,0.12)',
            border: '1px solid #dadce0'
          }}>
            {/* Modal Header */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid #f1f3f4', paddingBottom: '16px', marginBottom: '16px' }}>
              <div>
                <h2 style={{ fontSize: '18px', color: 'var(--accent-blue)', fontFamily: 'var(--font-display)', fontWeight: '500' }}>
                  Compliance Category: {selectedBucket}
                </h2>
                <span style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>
                  Found {activeIssues.length} matching issues (Critical & High priority sorted first)
                </span>
              </div>
              <button 
                onClick={() => setSelectedBucket(null)}
                style={{
                  background: 'none',
                  border: 'none',
                  fontSize: '24px',
                  color: 'var(--text-secondary)',
                  cursor: 'pointer',
                  padding: '4px'
                }}
              >
                &times;
              </button>
            </div>

            {/* Modal Filters Row */}
            <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap', marginBottom: '16px', padding: '12px', backgroundColor: '#f8f9fa', borderRadius: '6px', border: '1px solid #e0e0e0' }}>
              {/* Search text */}
              <input 
                type="text" 
                placeholder="Search SKU Name..." 
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                style={{
                  flex: '1.5',
                  minWidth: '180px',
                  padding: '8px 12px',
                  borderRadius: '4px',
                  border: '1px solid #dadce0',
                  fontSize: '13px',
                  outline: 'none'
                }}
              />
              
              {/* Severity filter */}
              <select
                value={severityFilter}
                onChange={(e) => setSeverityFilter(e.target.value)}
                style={{
                  flex: '1',
                  minWidth: '120px',
                  padding: '8px 12px',
                  borderRadius: '4px',
                  border: '1px solid #dadce0',
                  fontSize: '13px',
                  backgroundColor: '#fff',
                  outline: 'none'
                }}
              >
                <option value="ALL">All Severities</option>
                <option value="Critical">Critical Only</option>
                <option value="High">High Only</option>
                <option value="Medium">Medium Only</option>
                <option value="Low">Low Only</option>
              </select>

              {/* Domain Type filter */}
              <select
                value={typeFilter}
                onChange={(e) => setTypeFilter(e.target.value)}
                style={{
                  flex: '1',
                  minWidth: '120px',
                  padding: '8px 12px',
                  borderRadius: '4px',
                  border: '1px solid #dadce0',
                  fontSize: '13px',
                  backgroundColor: '#fff',
                  outline: 'none'
                }}
              >
                <option value="ALL">All Domains</option>
                <option value="COMPLETENESS">Completeness (MIS)</option>
                <option value="ACCURACY">Accuracy & Quality</option>
              </select>
            </div>

            {/* Modal Issues Table Grid */}
            <div style={{ flex: 1, overflowY: 'auto', paddingRight: '4px' }}>
              {activeIssues.length === 0 ? (
                <div style={{ textAlign: 'center', padding: '40px', color: 'var(--text-muted)' }}>
                  No active compliance tickets found matching your filter criteria.
                </div>
              ) : (
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
                  <thead>
                    <tr style={{ borderBottom: '2px solid #dadce0', textAlign: 'left', color: 'var(--text-secondary)' }}>
                      <th style={{ padding: '10px' }}>SKU Name</th>
                      <th style={{ padding: '10px' }}>Attribute Checked</th>
                      <th style={{ padding: '10px' }}>Severity</th>
                      <th style={{ padding: '10px' }}>Compliance Domain</th>
                      <th style={{ padding: '10px' }}>Suggested Correction</th>
                    </tr>
                  </thead>
                  <tbody>
                    {activeIssues.map((iss) => {
                      const med = getMedicineForIssue(iss.audit_record_id);
                      
                      // Severity style helper
                      let severityBg = '#e8f0fe';
                      let severityColor = '#1a73e8';
                      if (iss.severity === 'Critical') {
                        severityBg = '#fce8e6';
                        severityColor = '#c5221f';
                      } else if (iss.severity === 'High') {
                        severityBg = '#ffe0b2';
                        severityColor = '#e65100';
                      } else if (iss.severity === 'Medium') {
                        severityBg = '#fef7e0';
                        severityColor = '#b06000';
                      }

                      return (
                        <tr key={iss.id} style={{ borderBottom: '1px solid #dadce0' }}>
                          <td style={{ padding: '12px 10px', fontWeight: 'bold' }}>
                            {med.name}
                          </td>
                          <td style={{ padding: '12px 10px' }}>{iss.attribute}</td>
                          <td style={{ padding: '12px 10px' }}>
                            <span style={{
                              backgroundColor: severityBg,
                              color: severityColor,
                              padding: '3px 8px',
                              borderRadius: '4px',
                              fontWeight: 'bold',
                              fontSize: '11px',
                              display: 'inline-block'
                            }}>
                              {iss.severity}
                            </span>
                          </td>
                          <td style={{ padding: '12px 10px' }}>
                            <span style={{
                              backgroundColor: iss.issue_type === 'MIS' ? '#f3e5f5' : '#e2f1f8',
                              color: iss.issue_type === 'MIS' ? '#7b1fa2' : '#0288d1',
                              padding: '2px 6px',
                              borderRadius: '4px',
                              fontSize: '11px',
                              fontWeight: '600'
                            }}>
                              {iss.issue_type === 'MIS' ? 'Completeness' : 'Accuracy/Quality'}
                            </span>
                          </td>
                          <td style={{ padding: '12px 10px', color: 'var(--text-secondary)', fontStyle: 'italic' }}>
                            {iss.suggested_content || 'N/A'}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              )}
            </div>

            {/* Modal Footer */}
            <div style={{ display: 'flex', justifyContent: 'flex-end', borderTop: '1px solid #f1f3f4', paddingTop: '16px', marginTop: '16px' }}>
              <button 
                onClick={() => setSelectedBucket(null)}
                style={{
                  backgroundColor: 'var(--accent-blue)',
                  color: '#ffffff',
                  border: 'none',
                  borderRadius: '4px',
                  padding: '8px 16px',
                  fontSize: '13px',
                  fontWeight: '500',
                  cursor: 'pointer'
                }}
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
};
