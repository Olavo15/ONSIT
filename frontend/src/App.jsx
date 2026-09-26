import React, { useState, useEffect } from 'react';
import { 
  Shield, Search, Network, AlertTriangle, FileText, Database, 
  CheckCircle2, Clock, Eye, EyeOff, Lock, User, Phone, Mail, 
  Building2, Globe, Cpu, Hash, Share2, Download, AlertOctagon,
  ExternalLink, Layers, RefreshCw
} from 'lucide-react';

const API_BASE_URL = 'http://localhost:8000/api/v1';

export default function App() {
  const [activeTab, setActiveTab] = useState('new'); // 'new', 'findings', 'graph', 'complaints', 'sources', 'report'
  const [indicatorType, setIndicatorType] = useState('CPF');
  const [indicatorValue, setIndicatorValue] = useState('');
  const [subjectName, setSubjectName] = useState(''); // Nome opcional do titular
  
  const [isProcessing, setIsProcessing] = useState(false);
  const [progress, setProgress] = useState(0);
  const [currentInvestigation, setCurrentInvestigation] = useState(null);
  const [findings, setFindings] = useState([]);
  const [graphData, setGraphData] = useState({ nodes: [], edges: [] });
  const [sources, setSources] = useState([]);
  const [complaints, setComplaints] = useState([]);
  const [reportText, setReportText] = useState('');

  // Complaint Form State
  const [newComplaint, setNewComplaint] = useState({
    indicator_type: 'PHONE',
    indicator: '',
    report_type: 'SUSPECTED_SCAM',
    description: ''
  });

  const indicatorOptions = [
    { type: 'CPF', label: 'CPF', icon: User, placeholder: '000.000.000-00' },
    { type: 'CNPJ', label: 'CNPJ', icon: Building2, placeholder: '00.000.000/0001-00' },
    { type: 'PHONE', label: 'Telefone', icon: Phone, placeholder: '+55 88 99999-9999' },
    { type: 'EMAIL', label: 'E-mail', icon: Mail, placeholder: 'suspeito@email.com' },
    { type: 'PIX', label: 'Chave Pix', icon: ZapIcon, placeholder: 'CPF, CNPJ, telefone, email ou chave aleatória' },
    { type: 'DOMAIN', label: 'Domínio', icon: Globe, placeholder: 'empresa.com.br' },
    { type: 'URL', label: 'URL', icon: ExternalLink, placeholder: 'https://site-suspeito.com/login' },
    { type: 'USERNAME', label: 'Username', icon: User, placeholder: '@usuario' },
    { type: 'IP', label: 'Endereço IP', icon: Cpu, placeholder: '192.168.1.1' },
    { type: 'HASH', label: 'Hash MD5/SHA256', icon: Hash, placeholder: 'a1b2c3d4...' }
  ];

  // Helper for applying input masks dynamically per type
  const formatValueByMask = (val, type) => {
    if (!val) return '';
    const digits = val.replace(/\D/g, '');

    if (type === 'CPF') {
      const d = digits.slice(0, 11);
      if (d.length <= 3) return d;
      if (d.length <= 6) return `${d.slice(0, 3)}.${d.slice(3)}`;
      if (d.length <= 9) return `${d.slice(0, 3)}.${d.slice(3, 6)}.${d.slice(6)}`;
      return `${d.slice(0, 3)}.${d.slice(3, 6)}.${d.slice(6, 9)}-${d.slice(9)}`;
    } 
    
    if (type === 'CNPJ') {
      const d = digits.slice(0, 14);
      if (d.length <= 2) return d;
      if (d.length <= 5) return `${d.slice(0, 2)}.${d.slice(2)}`;
      if (d.length <= 8) return `${d.slice(0, 2)}.${d.slice(2, 5)}.${d.slice(5)}`;
      if (d.length <= 12) return `${d.slice(0, 2)}.${d.slice(2, 5)}.${d.slice(5, 8)}/${d.slice(8)}`;
      return `${d.slice(0, 2)}.${d.slice(2, 5)}.${d.slice(5, 8)}/${d.slice(8, 12)}-${d.slice(12)}`;
    } 
    
    if (type === 'PHONE') {
      const d = digits.slice(0, 13);
      if (d.length <= 2) return `+${d}`;
      if (d.length <= 4) return `+${d.slice(0, 2)} ${d.slice(2)}`;
      if (d.length <= 9) return `+${d.slice(0, 2)} ${d.slice(2, 4)} ${d.slice(4)}`;
      return `+${d.slice(0, 2)} ${d.slice(2, 4)} ${d.slice(4, 9)}-${d.slice(9)}`;
    } 

    if (type === 'USERNAME') {
      return val.startsWith('@') ? val : `@${val}`;
    }

    return val;
  };

  // Handle switching indicator type
  const handleTypeChange = (newType) => {
    setIndicatorType(newType);
    setIndicatorValue(''); // Apaga o campo ao mudar de tipo
  };

  const handleInputChange = (e) => {
    const rawVal = e.target.value;
    const masked = formatValueByMask(rawVal, indicatorType);
    setIndicatorValue(masked);
  };

  // Fetch sources on load
  useEffect(() => {
    fetch(`${API_BASE_URL}/sources`)
      .then(res => res.json())
      .then(data => setSources(data))
      .catch(() => {});

    fetch(`${API_BASE_URL}/complaints`)
      .then(res => res.json())
      .then(data => setComplaints(data))
      .catch(() => {});
  }, []);

  const handleStartInvestigation = async (e) => {
    e.preventDefault();
    if (!indicatorValue.trim()) return;

    setIsProcessing(true);
    setProgress(15);

    try {
      // 1. Create Investigation
      const res = await fetch(`${API_BASE_URL}/investigations`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: `Investigação [${indicatorType}] ${indicatorValue}`,
          subject_name: subjectName || undefined,
          indicators: [{ type: indicatorType, value: indicatorValue }]
        })
      });
      const data = await res.json();
      setCurrentInvestigation(data);

      // Simulate step progress while server processes
      let currentProgress = 30;
      const interval = setInterval(async () => {
        currentProgress += 20;
        if (currentProgress >= 90) {
          clearInterval(interval);
          
          // Fetch completed investigation
          const invRes = await fetch(`${API_BASE_URL}/investigations/${data.id}`);
          const invData = await invRes.json();
          setCurrentInvestigation(invData);

          // Fetch findings
          const findRes = await fetch(`${API_BASE_URL}/investigations/${data.id}/findings`);
          const findData = await findRes.json();
          setFindings(findData);

          // Fetch graph
          const graphRes = await fetch(`${API_BASE_URL}/investigations/${data.id}/graph`);
          const graphDataJson = await graphRes.json();
          setGraphData(graphDataJson);

          // Fetch report
          const repRes = await fetch(`${API_BASE_URL}/reports/${data.id}?format=TXT`);
          const repData = await repRes.json();
          setReportText(repData.content);

          setProgress(100);
          setIsProcessing(false);
          setActiveTab('findings');
        } else {
          setProgress(currentProgress);
        }
      }, 600);

    } catch (err) {
      console.error(err);
      setIsProcessing(false);
    }
  };

  const handleCreateComplaint = async (e) => {
    e.preventDefault();
    try {
      const res = await fetch(`${API_BASE_URL}/complaints`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newComplaint)
      });
      if (res.ok) {
        const data = await res.json();
        setComplaints([data, ...complaints]);
        setNewComplaint({ indicator_type: 'PHONE', indicator: '', report_type: 'SUSPECTED_SCAM', description: '' });
        alert('Denúncia registrada com sucesso no banco próprio!');
      }
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      {/* Header Bar */}
      <header className="glass-panel" style={{ borderRadius: 0, borderTop: 0, borderLeft: 0, borderRight: 0, padding: '16px 32px' }}>
        <div style={{ maxWidth: 1400, margin: '0 auto', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <div style={{
              background: 'linear-gradient(135deg, #0284c7, #7c3aed)',
              padding: 10, borderRadius: 12, display: 'flex', alignItems: 'center', justifyContent: 'center'
            }}>
              <Shield size={24} color="#fff" />
            </div>
            <div>
              <h1 style={{ fontFamily: 'var(--font-heading)', fontSize: '1.4rem', fontWeight: 700, color: '#fff' }}>
                fraud-recon <span style={{ color: 'var(--accent-cyan)', fontSize: '0.85rem', fontWeight: 400 }}>v1.0 OSINT</span>
              </h1>
              <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Plataforma de Investigação Antifraude & Correlação de Evidências</p>
            </div>
          </div>

          {/* Navigation Tabs */}
          <nav style={{ display: 'flex', gap: 8 }}>
            {[
              { id: 'new', label: 'Nova Consulta', icon: Search },
              { id: 'findings', label: `Evidências (${findings.length})`, icon: Database, disabled: !currentInvestigation },
              { id: 'graph', label: 'Grafo de Entidades', icon: Network, disabled: !currentInvestigation },
              { id: 'complaints', label: `Denúncias (${complaints.length})`, icon: AlertTriangle },
              { id: 'sources', label: 'Catálogo de Fontes', icon: Layers },
              { id: 'report', label: 'Relatório Final', icon: FileText, disabled: !currentInvestigation }
            ].map(tab => {
              const Icon = tab.icon;
              return (
                <button
                  key={tab.id}
                  disabled={tab.disabled}
                  onClick={() => setActiveTab(tab.id)}
                  style={{
                    background: activeTab === tab.id ? 'rgba(56, 189, 248, 0.15)' : 'transparent',
                    border: `1px solid ${activeTab === tab.id ? 'var(--accent-cyan)' : 'transparent'}`,
                    color: activeTab === tab.id ? 'var(--accent-cyan)' : 'var(--text-muted)',
                    padding: '8px 16px',
                    borderRadius: 10,
                    cursor: tab.disabled ? 'not-allowed' : 'pointer',
                    opacity: tab.disabled ? 0.4 : 1,
                    display: 'flex',
                    alignItems: 'center',
                    gap: 8,
                    fontSize: '0.9rem',
                    fontWeight: 500,
                    transition: 'all 0.2s'
                  }}
                >
                  <Icon size={16} />
                  {tab.label}
                </button>
              );
            })}
          </nav>
        </div>
      </header>

      {/* Main Content Area */}
      <main style={{ flex: 1, maxWidth: 1400, width: '100%', margin: '32px auto', padding: '0 24px' }}>
        
        {/* NEW INVESTIGATION TAB */}
        {activeTab === 'new' && (
          <div style={{ maxWidth: 840, margin: '0 auto' }}>
            <div className="glass-panel" style={{ padding: 40 }}>
              <div style={{ textAlign: 'center', marginBottom: 32 }}>
                <h2 style={{ fontFamily: 'var(--font-heading)', fontSize: '1.8rem', fontWeight: 700, marginBottom: 8 }}>
                  Iniciar Investigação Antifraude
                </h2>
                <p style={{ color: 'var(--text-muted)', fontSize: '0.95rem' }}>
                  Insira um identificador para consultar Receita Federal, DICT Pix, HIBP, RDAP, urlscan.io, GitHub e denúncias internas.
                </p>
              </div>

              {/* Indicator Type Buttons */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 10, marginBottom: 24 }}>
                {indicatorOptions.map(opt => {
                  const Icon = opt.icon;
                  const selected = indicatorType === opt.type;
                  return (
                    <button
                      key={opt.type}
                      type="button"
                      onClick={() => handleTypeChange(opt.type)}
                      style={{
                        background: selected ? 'rgba(56, 189, 248, 0.2)' : 'rgba(255,255,255,0.03)',
                        border: `1px solid ${selected ? 'var(--accent-cyan)' : 'rgba(255,255,255,0.08)'}`,
                        color: selected ? '#fff' : 'var(--text-muted)',
                        padding: '12px 8px',
                        borderRadius: 12,
                        cursor: 'pointer',
                        display: 'flex',
                        flexDirection: 'column',
                        alignItems: 'center',
                        gap: 6,
                        fontSize: '0.8rem',
                        fontWeight: 500,
                        transition: 'all 0.2s'
                      }}
                    >
                      <Icon size={18} color={selected ? 'var(--accent-cyan)' : 'var(--text-muted)'} />
                      {opt.label}
                    </button>
                  );
                })}
              </div>

              {/* Input Form with Real-time Masking */}
              <form onSubmit={handleStartInvestigation}>
                <div style={{ marginBottom: 16 }}>
                  <label style={{ display: 'block', fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: 6 }}>
                    Identificador de Consulta ({indicatorType})
                  </label>
                  <input
                    type="text"
                    required
                    value={indicatorValue}
                    onChange={handleInputChange}
                    placeholder={`Exemplo (${indicatorType}): ${indicatorOptions.find(o => o.type === indicatorType)?.placeholder}`}
                    style={{
                      width: '100%',
                      background: 'rgba(0,0,0,0.4)',
                      border: '1px solid var(--border-color)',
                      borderRadius: 14,
                      padding: '16px 20px',
                      color: '#fff',
                      fontSize: '1.1rem',
                      fontFamily: 'var(--font-mono)',
                      outline: 'none'
                    }}
                  />
                </div>

                <button
                  type="submit"
                  disabled={isProcessing || !indicatorValue.trim()}
                  className="glow-btn"
                  style={{ width: '100%', justifyContent: 'center', padding: '16px', fontSize: '1.05rem' }}
                >
                  {isProcessing ? (
                    <>
                      <RefreshCw size={20} className="pulse-glow" style={{ animation: 'spin 1s linear infinite' }} />
                      Coletando Evidências... ({progress}%)
                    </>
                  ) : (
                    <>
                      <Search size={20} />
                      Executar Investigação Multi-Fonte
                    </>
                  )}
                </button>
              </form>

              {/* Progress Indicator */}
              {isProcessing && (
                <div style={{ marginTop: 32 }}>
                  <div style={{ background: 'rgba(255,255,255,0.05)', borderRadius: 10, height: 8, overflow: 'hidden', marginBottom: 16 }}>
                    <div style={{ background: 'linear-gradient(90deg, var(--accent-cyan), var(--accent-purple))', width: `${progress}%`, height: '100%', transition: 'width 0.4s ease' }} />
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12, fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6, color: progress >= 20 ? 'var(--accent-emerald)' : 'var(--text-dim)' }}>
                      <CheckCircle2 size={14} /> Normalização
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6, color: progress >= 50 ? 'var(--accent-emerald)' : 'var(--text-dim)' }}>
                      <CheckCircle2 size={14} /> Fontes Públicas
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6, color: progress >= 80 ? 'var(--accent-emerald)' : 'var(--text-dim)' }}>
                      <CheckCircle2 size={14} /> Resolutor de Grafo
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6, color: progress >= 100 ? 'var(--accent-emerald)' : 'var(--text-dim)' }}>
                      <CheckCircle2 size={14} /> Relatório Final
                    </div>
                  </div>
                </div>
              )}

              {/* LGPD Disclaimer */}
              <div style={{ marginTop: 32, padding: 16, borderRadius: 12, background: 'rgba(245, 158, 11, 0.08)', border: '1px solid rgba(245, 158, 11, 0.2)', display: 'flex', gap: 12, alignItems: 'flex-start' }}>
                <AlertTriangle size={20} color="var(--accent-amber)" style={{ flexShrink: 0, marginTop: 2 }} />
                <div style={{ fontSize: '0.82rem', color: 'var(--text-muted)', lineHeight: 1.5 }}>
                  <strong style={{ color: 'var(--accent-amber)' }}>Princípio de Responsabilidade & LGPD:</strong> O sistema consolida fatos, evidências e proveniências de fontes públicas autorizadas. Relatos de usuários são identificados separadamente de fatos confirmados.
                </div>
              </div>
            </div>
          </div>
        )}

        {/* FINDINGS TAB */}
        {activeTab === 'findings' && (
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
              <div>
                <h2 style={{ fontFamily: 'var(--font-heading)', fontSize: '1.6rem', fontWeight: 700 }}>
                  Evidências Coletadas ({findings.length})
                </h2>
                <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>
                  {currentInvestigation?.title} | Status: <span style={{ color: 'var(--accent-emerald)' }}>CONCLUÍDO</span>
                </p>
              </div>
              <button onClick={() => setActiveTab('graph')} className="glow-btn" style={{ padding: '8px 16px', fontSize: '0.85rem' }}>
                <Network size={16} /> Ver Grafo de Relacionamentos
              </button>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(400px, 1fr))', gap: 16 }}>
              {findings.map(f => (
                <div key={f.id} className="glass-panel" style={{ padding: 20 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 12 }}>
                    <div>
                      <span className="badge badge-confirmed" style={{ marginBottom: 6 }}>
                        {f.source_name}
                      </span>
                      <h4 style={{ fontSize: '1.05rem', fontWeight: 600, color: '#fff' }}>{f.field}</h4>
                    </div>
                    <span className={`badge ${f.display_policy === 'FULL' ? 'badge-policy-full' : 'badge-policy-masked'}`}>
                      {f.display_policy}
                    </span>
                  </div>

                  <div style={{
                    background: 'rgba(0,0,0,0.3)',
                    padding: 12,
                    borderRadius: 8,
                    fontFamily: 'var(--font-mono)',
                    fontSize: '0.9rem',
                    color: 'var(--accent-cyan)',
                    marginBottom: 12,
                    wordBreak: 'break-all',
                    whiteSpace: 'pre-wrap'
                  }}>
                    {f.value}
                  </div>

                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.78rem', color: 'var(--text-dim)' }}>
                    <span>Ref: {f.source_reference || 'Direta'}</span>
                    <span>Status: {f.verification_status}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* GRAPH TAB */}
        {activeTab === 'graph' && (
          <div>
            <div style={{ marginBottom: 24 }}>
              <h2 style={{ fontFamily: 'var(--font-heading)', fontSize: '1.6rem', fontWeight: 700 }}>
                Grafo de Relacionamentos e Entidades
              </h2>
              <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>Visualização de nós de vínculo (Entidades, Empresas, Telefones, Domínios, IPs)</p>
            </div>

            <div className="glass-panel" style={{ padding: 32, minHeight: 500, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
              <svg width="100%" height="400" viewBox="0 0 800 400" style={{ background: 'rgba(0,0,0,0.2)', borderRadius: 12 }}>
                {/* Visual SVG Node Network */}
                <line x1="400" y1="200" x2="250" y2="100" stroke="var(--accent-cyan)" strokeWidth="2" strokeDasharray="4" />
                <line x1="400" y1="200" x2="550" y2="100" stroke="var(--accent-purple)" strokeWidth="2" />
                <line x1="400" y1="200" x2="250" y2="300" stroke="var(--accent-emerald)" strokeWidth="2" />
                <line x1="400" y1="200" x2="550" y2="300" stroke="var(--accent-amber)" strokeWidth="2" />

                {/* Central Node */}
                <circle cx="400" cy="200" r="35" fill="var(--accent-cyan)" opacity="0.2" className="pulse-glow" />
                <circle cx="400" cy="200" r="24" fill="#0284c7" stroke="#38bdf8" strokeWidth="2" />
                <text x="400" y="205" textAnchor="middle" fill="#fff" fontSize="12" fontWeight="bold">Investigação</text>

                {/* Connected Nodes */}
                {graphData.nodes.map((node, i) => {
                  const coords = [
                    { x: 250, y: 100 },
                    { x: 550, y: 100 },
                    { x: 250, y: 300 },
                    { x: 550, y: 300 }
                  ][i % 4];

                  return (
                    <g key={node.id}>
                      <circle cx={coords.x} cy={coords.y} r="18" fill="#1e293b" stroke="var(--accent-purple)" strokeWidth="2" />
                      <text x={coords.x} y={coords.y + 32} textAnchor="middle" fill="var(--text-main)" fontSize="11">{node.name.slice(0, 25)}</text>
                    </g>
                  );
                })}
              </svg>

              <div style={{ marginTop: 24, display: 'flex', gap: 24, fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                <span>• Nó Principal: Sujeito Investigado</span>
                <span>• Vínculos: CNPJ / Domínio / E-mail / Telefone / IP</span>
              </div>
            </div>
          </div>
        )}

        {/* COMPLAINTS TAB */}
        {activeTab === 'complaints' && (
          <div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: 24 }}>
              {/* Form */}
              <div className="glass-panel" style={{ padding: 24 }}>
                <h3 style={{ fontFamily: 'var(--font-heading)', fontSize: '1.2rem', fontWeight: 700, marginBottom: 16 }}>
                  Registrar Nova Denúncia
                </h3>
                <form onSubmit={handleCreateComplaint}>
                  <div style={{ marginBottom: 16 }}>
                    <label style={{ display: 'block', fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: 6 }}>Tipo de Indicador</label>
                    <select
                      value={newComplaint.indicator_type}
                      onChange={e => setNewComplaint({...newComplaint, indicator_type: e.target.value})}
                      style={{ width: '100%', background: 'rgba(0,0,0,0.3)', border: '1px solid var(--border-color)', color: '#fff', padding: 10, borderRadius: 8 }}
                    >
                      <option value="PHONE">Telefone</option>
                      <option value="EMAIL">E-mail</option>
                      <option value="CPF">CPF</option>
                      <option value="CNPJ">CNPJ</option>
                      <option value="PIX">Chave Pix</option>
                      <option value="URL">URL</option>
                    </select>
                  </div>

                  <div style={{ marginBottom: 16 }}>
                    <label style={{ display: 'block', fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: 6 }}>Indicador (Valor)</label>
                    <input
                      type="text"
                      required
                      value={newComplaint.indicator}
                      onChange={e => setNewComplaint({...newComplaint, indicator: e.target.value})}
                      placeholder="+558899999999"
                      style={{ width: '100%', background: 'rgba(0,0,0,0.3)', border: '1px solid var(--border-color)', color: '#fff', padding: 10, borderRadius: 8, fontFamily: 'var(--font-mono)' }}
                    />
                  </div>

                  <div style={{ marginBottom: 16 }}>
                    <label style={{ display: 'block', fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: 6 }}>Descrição do Relato</label>
                    <textarea
                      required
                      rows={4}
                      value={newComplaint.description}
                      onChange={e => setNewComplaint({...newComplaint, description: e.target.value})}
                      placeholder="Descreva o ocorrido de forma factual..."
                      style={{ width: '100%', background: 'rgba(0,0,0,0.3)', border: '1px solid var(--border-color)', color: '#fff', padding: 10, borderRadius: 8 }}
                    />
                  </div>

                  <button type="submit" className="glow-btn" style={{ width: '100%', justifyContent: 'center' }}>
                    Registrar Denúncia
                  </button>
                </form>
              </div>

              {/* Complaints List */}
              <div>
                <h3 style={{ fontFamily: 'var(--font-heading)', fontSize: '1.2rem', fontWeight: 700, marginBottom: 16 }}>
                  Denúncias Cadastradas ({complaints.length})
                </h3>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                  {complaints.map(c => (
                    <div key={c.id} className="glass-panel" style={{ padding: 16 }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                        <span className="badge badge-user">{c.indicator_type}: {c.indicator}</span>
                        <span style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>
                          {new Date(c.reported_at).toLocaleDateString('pt-BR')}
                        </span>
                      </div>
                      <p style={{ fontSize: '0.9rem', color: 'var(--text-main)', lineHeight: 1.4 }}>{c.description}</p>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* SOURCES TAB */}
        {activeTab === 'sources' && (
          <div>
            <div style={{ marginBottom: 24 }}>
              <h2 style={{ fontFamily: 'var(--font-heading)', fontSize: '1.6rem', fontWeight: 700 }}>
                Catálogo Inicial de Fontes & APIs Autorizadas
              </h2>
              <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>Mapeamento oficial de integrações de inteligência OSINT (Seção 27)</p>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: 16 }}>
              {sources.map((s, i) => (
                <div key={i} className="glass-panel" style={{ padding: 20 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
                    <h4 style={{ fontSize: '1.1rem', fontWeight: 600, color: 'var(--accent-cyan)' }}>{s.name}</h4>
                    <span className="badge badge-confirmed">{s.type}</span>
                  </div>
                  <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>{s.utilidade}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* REPORT TAB */}
        {activeTab === 'report' && (
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
              <div>
                <h2 style={{ fontFamily: 'var(--font-heading)', fontSize: '1.6rem', fontWeight: 700 }}>
                  Relatório Consolidado de Investigação
                </h2>
                <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>Conforme modelo padronizado da Seção 28</p>
              </div>
              <button
                onClick={() => {
                  const element = document.createElement("a");
                  const file = new Blob([reportText], {type: 'text/plain'});
                  element.href = URL.createObjectURL(file);
                  element.download = `relatorio_${currentInvestigation?.id}.txt`;
                  document.body.appendChild(element);
                  element.click();
                }}
                className="glow-btn"
                style={{ padding: '8px 16px', fontSize: '0.85rem' }}
              >
                <Download size={16} /> Baixar Relatório (TXT)
              </button>
            </div>

            <div className="glass-panel" style={{ padding: 32 }}>
              <pre style={{
                fontFamily: 'var(--font-mono)',
                fontSize: '0.95rem',
                color: 'var(--accent-cyan)',
                background: 'rgba(0,0,0,0.5)',
                padding: 24,
                borderRadius: 12,
                whiteSpace: 'pre-wrap',
                lineHeight: 1.6
              }}>
                {reportText}
              </pre>
            </div>
          </div>
        )}

      </main>
    </div>
  );
}

// Zap Icon helper for Pix
function ZapIcon(props) {
  return (
    <svg {...props} width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"></polygon>
    </svg>
  );
}
