import React from 'react';

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

interface DashboardViewProps {
  summary: SummaryData;
  heatmap: Record<string, number>;
  trends: TrendPoint[];
}

export const DashboardView: React.FC<DashboardViewProps> = ({ summary, heatmap, trends }) => {
  // Score circle rendering helper
  const renderScoreCircle = (score: number, title: string, subtitle: string, color: string) => {
    const radius = 50;
    const strokeWidth = 8;
    const circumference = 2 * Math.PI * radius;
    const offset = circumference - (score / 100) * circumference;

    return (
      <div className="glass-panel" style={{ padding: '24px', display: 'flex', flexDirection: 'column', alignItems: 'center', flex: '1', minWidth: '240px' }}>
        <div style={{ position: 'relative', width: '120px', height: '120px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <svg style={{ transform: 'rotate(-90deg)', width: '120px', height: '120px' }}>
            <circle cx="60" cy="60" r={radius} fill="transparent" stroke="rgba(255, 255, 255, 0.05)" strokeWidth={strokeWidth} />
            <circle cx="60" cy="60" r={radius} fill="transparent" stroke={color} strokeWidth={strokeWidth} strokeDasharray={circumference} strokeDashoffset={offset} strokeLinecap="round" style={{ transition: 'stroke-dashoffset 0.5s ease' }} />
          </svg>
          <div style={{ position: 'absolute', display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
            <span style={{ fontSize: '24px', fontWeight: 'bold', fontFamily: 'var(--font-display)' }}>{score}%</span>
            <span style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>{subtitle}</span>
          </div>
        </div>
        <h3 style={{ marginTop: '16px', fontSize: '16px', fontWeight: '600' }}>{title}</h3>
      </div>
    );
  };

  // SVG Trend Chart
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

    return (
      <svg viewBox={`0 0 ${width} ${height}`} style={{ width: '100%', height: 'auto', maxHeight: '280px' }}>
        {/* Y Axis gridlines */}
        {[0, 25, 50, 75, 100].map((gridVal) => {
          const y = getY(gridVal);
          return (
            <g key={gridVal}>
              <line x1={padding} y1={y} x2={width - padding} y2={y} stroke="rgba(255, 255, 255, 0.05)" strokeWidth="1" />
              <text x={padding - 10} y={y + 4} fill="var(--text-muted)" fontSize="10" textAnchor="end">{gridVal}</text>
            </g>
          );
        })}
        
        {/* Render paths */}
        <path d={accuracyPath} fill="transparent" stroke="var(--accent-blue)" strokeWidth="3" strokeLinecap="round" />
        <path d={completenessPath} fill="transparent" stroke="var(--accent-purple)" strokeWidth="3" strokeLinecap="round" />
        <path d={healthPath} fill="transparent" stroke="var(--status-success)" strokeWidth="4" strokeLinecap="round" />
        
        {/* Render points */}
        {trends.map((pt, idx) => (
          <circle key={idx} cx={getX(idx)} cy={getY(pt.health)} r="4" fill="var(--status-success)" stroke="var(--bg-secondary)" strokeWidth="2" />
        ))}
      </svg>
    );
  };

  // Get color for density cell
  const getDensityColor = (count: number) => {
    if (count === 0) return 'rgba(0, 245, 212, 0.1)';
    if (count < 3) return 'rgba(254, 228, 64, 0.2)';
    if (count < 6) return 'rgba(255, 0, 127, 0.4)';
    return 'rgba(255, 0, 127, 0.8)';
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      
      {/* 1. Score Summary Row */}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '24px' }}>
        {renderScoreCircle(summary.overall_content_health_score, "Content Health Score", "Weighted Score", "var(--status-success)")}
        {renderScoreCircle(summary.overall_medical_accuracy_score, "Medical Accuracy Score", "AI-Audited", "var(--accent-blue)")}
        {renderScoreCircle(summary.overall_completeness_score, "Completeness Score", "Completeness", "var(--accent-purple)")}
      </div>

      {/* 2. Operational KPIs Row */}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '24px' }}>
        {/* Core numbers */}
        <div className="glass-panel" style={{ padding: '24px', flex: '1', minWidth: '280px', display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '16px' }}>
          <div>
            <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>Total Registered SKU</div>
            <div style={{ fontSize: '32px', fontWeight: 'bold', marginTop: '4px' }}>{summary.total_urls}</div>
          </div>
          <div>
            <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>Completed Scrapes</div>
            <div style={{ fontSize: '32px', fontWeight: 'bold', marginTop: '4px', color: 'var(--accent-blue)' }}>{summary.urls_scraped}</div>
          </div>
          <div>
            <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>Total Audit Cases</div>
            <div style={{ fontSize: '32px', fontWeight: 'bold', marginTop: '4px', color: 'var(--accent-purple)' }}>{summary.urls_audited}</div>
          </div>
          <div>
            <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>Active Open Issues</div>
            <div style={{ fontSize: '32px', fontWeight: 'bold', marginTop: '4px', color: 'var(--status-danger)' }}>{summary.open_issues}</div>
          </div>
        </div>

        {/* Severity list */}
        <div className="glass-panel" style={{ padding: '24px', flex: '1', minWidth: '280px' }}>
          <h3 style={{ fontSize: '16px', marginBottom: '16px', fontWeight: '600' }}>Compliance Issues by Severity</h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: '13px', color: 'var(--status-danger)', fontWeight: 'bold' }}>🔴 Critical Issues</span>
              <span style={{ fontSize: '16px', fontWeight: 'bold' }}>{summary.critical_issues}</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: '13px', color: '#ff7b00', fontWeight: 'bold' }}>🟠 High Issues</span>
              <span style={{ fontSize: '16px', fontWeight: 'bold' }}>{summary.high_issues}</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: '13px', color: 'var(--status-warning)', fontWeight: 'bold' }}>🟡 Medium Issues</span>
              <span style={{ fontSize: '16px', fontWeight: 'bold' }}>{summary.medium_issues}</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: '13px', color: 'var(--accent-blue)', fontWeight: 'bold' }}>🔵 Low Issues</span>
              <span style={{ fontSize: '16px', fontWeight: 'bold' }}>{summary.low_issues}</span>
            </div>
          </div>
        </div>
      </div>

      {/* 3. Deep visual metrics (Heatmap + Trends) */}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '24px' }}>
        
        {/* Historical Trends chart */}
        <div className="glass-panel" style={{ padding: '24px', flex: '2', minWidth: '350px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
            <h3 style={{ fontSize: '16px', fontWeight: '600' }}>Governance Trend Analysis</h3>
            <div style={{ display: 'flex', gap: '12px', fontSize: '11px' }}>
              <span style={{ color: 'var(--status-success)' }}>● Health</span>
              <span style={{ color: 'var(--accent-blue)' }}>● Accuracy</span>
              <span style={{ color: 'var(--accent-purple)' }}>  ● Completeness</span>
            </div>
          </div>
          {renderTrendChart()}
        </div>

        {/* Heatmap density grid */}
        <div className="glass-panel" style={{ padding: '24px', flex: '1.2', minWidth: '280px' }}>
          <h3 style={{ fontSize: '16px', fontWeight: '600', marginBottom: '20px' }}>Compliance Risk Heatmap</h3>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '12px' }}>
            {['Safety', 'FAQs', 'Metadata', 'Core Medical Content', 'Drug Interactions'].map((bucket) => {
              const count = heatmap[bucket] || 0;
              return (
                <div 
                  key={bucket} 
                  style={{
                    padding: '16px', 
                    borderRadius: '12px', 
                    backgroundColor: getDensityColor(count),
                    border: '1px solid rgba(255,255,255,0.05)',
                    display: 'flex',
                    flexDirection: 'column',
                    justifyContent: 'space-between',
                    minHeight: '90px'
                  }}
                >
                  <span style={{ fontSize: '12px', color: 'var(--text-secondary)', fontWeight: '500' }}>{bucket}</span>
                  <span style={{ fontSize: '20px', fontWeight: 'bold', marginTop: '8px' }}>{count} {count === 1 ? 'Issue' : 'Issues'}</span>
                </div>
              );
            })}
          </div>
        </div>

      </div>

    </div>
  );
};
