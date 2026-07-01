import React, { useState } from 'react';

interface Medicine {
  id: number;
  url: string;
  name: string | null;
  generic_name: string | null;
  priority: string;
  owner: string | null;
  category: string | null;
}

interface AuditRecord {
  id: string;
  medicine_id: number;
  status: string;
  completeness_score: number | null;
  medical_accuracy_score: number | null;
  content_health_score: number | null;
  seo_score: number | null;
  geo_score: number | null;
  html_path: string | null;
  pdf_path: string | null;
  screenshot_path: string | null;
  json_path: string | null;
}

interface MedicinesViewProps {
  medicines: Medicine[];
  audits: AuditRecord[];
  onUploadExcel: (file: File) => Promise<void>;
  onTriggerScrape: (medId: number) => Promise<void>;
  onTriggerAudit: (auditId: string) => Promise<void>;
  loading: boolean;
}

export const MedicinesView: React.FC<MedicinesViewProps> = ({
  medicines,
  audits,
  onUploadExcel,
  onTriggerScrape,
  onTriggerAudit,
  loading
}) => {
  const [file, setFile] = useState<File | null>(null);
  const [dragActive, setDragActive] = useState<boolean>(false);
  const [filterPriority, setFilterPriority] = useState<string>("ALL");

  // Get the latest audit run for a specific medicine
  const getLatestAudit = (medId: number): AuditRecord | undefined => {
    return audits
      .filter(a => a.medicine_id === medId)
      .sort((a, b) => b.id.localeCompare(a.id))[0];
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
    }
  };

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      setFile(e.dataTransfer.files[0]);
    }
  };

  const handleUploadClick = async () => {
    if (file) {
      await onUploadExcel(file);
      setFile(null);
    }
  };

  // Filter medicines based on priority selection
  const filteredMedicines = filterPriority === "ALL" 
    ? medicines 
    : medicines.filter(m => m.priority.toUpperCase() === filterPriority);

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'Pending': return '#fee440'; // warning
      case 'Scraped': return '#00d2ff'; // info
      case 'Completeness_Checked': return '#9d4edd'; // purple
      case 'Audited': return '#00f5d4'; // success
      case 'Failed': return '#ff007f'; // danger
      default: return 'var(--text-muted)';
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '28px' }}>
      
      {/* 1. File Upload Dropzone */}
      <div className="glass-panel" style={{ padding: '24px' }}>
        <h3 style={{ fontSize: '18px', fontWeight: '600', marginBottom: '16px' }}>Catalog Ingestion</h3>
        
        <div 
          onDragEnter={handleDrag}
          onDragOver={handleDrag}
          onDragLeave={handleDrag}
          onDrop={handleDrop}
          style={{
            border: dragActive ? '2px dashed var(--accent-blue)' : '2px dashed rgba(255, 255, 255, 0.1)',
            borderRadius: '12px',
            padding: '30px',
            textAlign: 'center',
            cursor: 'pointer',
            backgroundColor: dragActive ? 'rgba(0, 210, 255, 0.03)' : 'rgba(255, 255, 255, 0.01)',
            transition: 'all 0.2s ease',
            position: 'relative'
          }}
        >
          <input 
            type="file" 
            accept=".xlsx, .xls"
            onChange={handleFileChange}
            style={{
              position: 'absolute',
              top: 0,
              left: 0,
              width: '100%',
              height: '100%',
              opacity: 0,
              cursor: 'pointer'
            }}
          />
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', pointerEvents: 'none' }}>
            <span style={{ fontSize: '15px', color: 'var(--text-primary)', fontWeight: '500' }}>
              {file ? `Selected file: ${file.name}` : "Drag and drop input.xlsx here or click to browse"}
            </span>
            <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
              Excel sheets containing Medicine URL, Product Name, Priority, Owner, and Category
            </span>
          </div>
        </div>

        {file && (
          <button 
            onClick={handleUploadClick}
            disabled={loading}
            style={{
              marginTop: '16px',
              padding: '10px 20px',
              borderRadius: '8px',
              border: 'none',
              background: 'linear-gradient(135deg, var(--accent-blue) 0%, var(--accent-purple) 100%)',
              color: '#fff',
              fontSize: '14px',
              fontWeight: '600',
              cursor: loading ? 'not-allowed' : 'pointer',
              opacity: loading ? 0.6 : 1
            }}
          >
            Import Excel Catalog
          </button>
        )}
      </div>

      {/* 2. Medicine SKU Table */}
      <div className="glass-panel" style={{ padding: '24px', overflowX: 'auto' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px', flexWrap: 'wrap', gap: '12px' }}>
          <h3 style={{ fontSize: '18px', fontWeight: '600' }}>Registered SKUs</h3>
          
          {/* Priority filter */}
          <div style={{ display: 'flex', gap: '8px' }}>
            {["ALL", "HIGH", "MEDIUM", "LOW"].map(p => (
              <button 
                key={p} 
                onClick={() => setFilterPriority(p)}
                style={{
                  padding: '6px 12px',
                  borderRadius: '6px',
                  border: '1px solid rgba(255, 255, 255, 0.05)',
                  fontSize: '12px',
                  fontWeight: '500',
                  cursor: 'pointer',
                  backgroundColor: filterPriority === p ? 'var(--bg-tertiary)' : 'var(--bg-secondary)',
                  color: filterPriority === p ? 'var(--accent-blue)' : 'var(--text-secondary)'
                }}
              >
                {p}
              </button>
            ))}
          </div>
        </div>

        {filteredMedicines.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '40px 0', color: 'var(--text-muted)', fontSize: '14px' }}>
            No medicine URLs registered. Upload an excel catalog sheet to start.
          </div>
        ) : (
          <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '13px' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.08)', color: 'var(--text-secondary)' }}>
                <th style={{ padding: '12px 8px' }}>ID</th>
                <th style={{ padding: '12px 8px' }}>Medicine Title</th>
                <th style={{ padding: '12px 8px' }}>Category</th>
                <th style={{ padding: '12px 8px' }}>Priority</th>
                <th style={{ padding: '12px 8px' }}>Owner</th>
                <th style={{ padding: '12px 8px' }}>Latest Audit</th>
                <th style={{ padding: '12px 8px' }}>Governance Score</th>
                <th style={{ padding: '12px 8px', textAlign: 'right' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredMedicines.map((med) => {
                const latestAudit = getLatestAudit(med.id);
                return (
                  <tr key={med.id} style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.05)', verticalAlign: 'middle' }}>
                    <td style={{ padding: '16px 8px', color: 'var(--text-muted)' }}>#{med.id}</td>
                    <td style={{ padding: '16px 8px' }}>
                      <div style={{ fontWeight: '600' }}>{med.name || "Extracting..."}</div>
                      <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '2px', wordBreak: 'break-all', maxWidth: '280px' }}>
                        {med.url}
                      </div>
                    </td>
                    <td style={{ padding: '16px 8px', color: 'var(--text-secondary)' }}>{med.category || "N/A"}</td>
                    <td style={{ padding: '16px 8px' }}>
                      <span style={{
                        padding: '3px 8px',
                        borderRadius: '4px',
                        fontSize: '11px',
                        fontWeight: 'bold',
                        backgroundColor: med.priority === 'High' ? 'rgba(255,0,127,0.1)' : 'rgba(255,255,255,0.05)',
                        color: med.priority === 'High' ? 'var(--accent-pink)' : 'var(--text-secondary)'
                      }}>
                        {med.priority}
                      </span>
                    </td>
                    <td style={{ padding: '16px 8px', color: 'var(--text-secondary)' }}>{med.owner || "Unassigned"}</td>
                    <td style={{ padding: '16px 8px' }}>
                      {latestAudit ? (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                          <span style={{
                            fontSize: '11px',
                            fontWeight: '600',
                            color: getStatusColor(latestAudit.status)
                          }}>
                            ● {latestAudit.status.replace('_', ' ')}
                          </span>
                          <span style={{ fontSize: '10px', color: 'var(--text-muted)' }}>{latestAudit.id}</span>
                        </div>
                      ) : (
                        <span style={{ color: 'var(--text-muted)' }}>Not Scraped</span>
                      )}
                    </td>
                    <td style={{ padding: '16px 8px' }}>
                      {latestAudit && latestAudit.content_health_score !== null ? (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
                          <span style={{ fontWeight: 'bold', color: 'var(--status-success)', fontSize: '14px' }}>
                            {latestAudit.content_health_score}%
                          </span>
                          <span style={{ fontSize: '10px', color: 'var(--text-muted)' }}>
                            Comp: {latestAudit.completeness_score}% | Acc: {latestAudit.medical_accuracy_score}% | SEO: {latestAudit.seo_score || 0}% | GEO: {latestAudit.geo_score || 0}%
                          </span>
                        </div>
                      ) : latestAudit && latestAudit.completeness_score !== null ? (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
                          <span style={{ fontWeight: 'bold', color: 'var(--accent-purple)', fontSize: '13px' }}>
                            Comp: {latestAudit.completeness_score}%
                          </span>
                          <span style={{ fontSize: '10px', color: 'var(--text-muted)' }}>Pending AI Audit</span>
                        </div>
                      ) : (
                        <span style={{ color: 'var(--text-muted)' }}>--</span>
                      )}
                    </td>
                    <td style={{ padding: '16px 8px', textAlign: 'right' }}>
                      <div style={{ display: 'inline-flex', gap: '8px' }}>
                        {(!latestAudit || latestAudit.status === 'Failed') && (
                          <button 
                            onClick={() => onTriggerScrape(med.id)}
                            disabled={loading}
                            className="glow-active"
                            style={{
                              padding: '6px 12px',
                              borderRadius: '6px',
                              border: 'none',
                              backgroundColor: 'var(--accent-blue)',
                              color: '#000',
                              fontWeight: '600',
                              cursor: 'pointer'
                            }}
                          >
                            Scrape SKU
                          </button>
                        )}
                        {latestAudit && latestAudit.status === 'Completeness_Checked' && (
                          <button 
                            onClick={() => onTriggerAudit(latestAudit.id)}
                            disabled={loading}
                            style={{
                              padding: '6px 12px',
                              borderRadius: '6px',
                              border: 'none',
                              backgroundColor: 'var(--accent-purple)',
                              color: '#fff',
                              fontWeight: '600',
                              cursor: 'pointer'
                            }}
                          >
                            Run AI Audit
                          </button>
                        )}
                        {latestAudit && latestAudit.status === 'Audited' && (
                          <button 
                            onClick={() => onTriggerScrape(med.id)}
                            disabled={loading}
                            style={{
                              padding: '6px 12px',
                              borderRadius: '6px',
                              border: '1px solid rgba(255,255,255,0.08)',
                              backgroundColor: 'transparent',
                              color: 'var(--text-secondary)',
                              fontWeight: '500',
                              cursor: 'pointer'
                            }}
                          >
                            Re-Scrape
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>

    </div>
  );
};
