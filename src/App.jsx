import { useMemo, useState } from 'react'
import catalogue from './data/catalogue.json'
import stats from './data/stats.json'
import './App.css'

const requestedGroups = [
  'Front bumper','Rear bumper','Headlights','Taillights','Side mirrors','Brake pads','Brake discs','Filters','Engine cooling','Engine internals','Emissions','Clutch','Hubs','Other'
]

function uniq(values){ return [...new Set(values.filter(Boolean))].sort((a,b)=>a.localeCompare(b)) }
function includes(haystack, needle){ return String(haystack||'').toLowerCase().includes(String(needle||'').toLowerCase()) }
function csvEscape(v){ return `"${String(v ?? '').replaceAll('"','""')}"` }

function App() {
  const [q,setQ]=useState('')
  const [brand,setBrand]=useState('')
  const [model,setModel]=useState('')
  const [group,setGroup]=useState('')
  const [grade,setGrade]=useState('')
  const [selected,setSelected]=useState(catalogue[0])

  const brands=useMemo(()=>uniq(catalogue.map(r=>r.brand)),[])
  const models=useMemo(()=>uniq(catalogue.filter(r=>!brand || r.brand===brand).map(r=>r.model)),[brand])
  const filtered=useMemo(()=>catalogue.filter(r=>{
    const blob=[r.id,r.brand,r.model,r.segment,r.category,r.group,r.part,r.position,r.oe,r.alt,r.sourceFile,r.sourceLine,r.notes].join(' ')
    return (!q || includes(blob,q)) && (!brand || r.brand===brand) && (!model || r.model===model) && (!group || r.group===group) && (!grade || r.gradeRank===Number(grade))
  }),[q,brand,model,group,grade])

  const quality = useMemo(()=>({
    confirmed: filtered.filter(r=>r.oe && !r.oe.toLowerCase().includes('not confirmed')).length,
    high: filtered.filter(r=>r.gradeRank===3).length,
    medium: filtered.filter(r=>r.gradeRank===2).length,
    low: filtered.filter(r=>r.gradeRank===1).length
  }),[filtered])

  function exportCsv(){
    const headers=['id','brand','model','segment','group','category','part','position','oe','alt','confidence','sourceFile','sourceLine','notes','supplierQuestion']
    const body=[headers.join(','),...filtered.map(r=>headers.map(h=>csvEscape(r[h])).join(','))].join('\n')
    const blob=new Blob([body],{type:'text/csv;charset=utf-8'})
    const url=URL.createObjectURL(blob); const a=document.createElement('a'); a.href=url; a.download='china-tecdoc-filtered-catalogue.csv'; a.click(); URL.revokeObjectURL(url)
  }

  return <main>
    <section className="hero">
      <div className="heroCopy">
        <p className="eyebrow">CHINAPAL · Chinese OEM Parts Intelligence</p>
        <h1>TecDoc-grade catalogue for Chinese cars, utilitaires, trucks and heavy trucks.</h1>
        <p className="lead">A premium Moroccan sourcing interface built from manufacturer/supplier catalogue evidence — searchable by brand, model, OE/OEM, system group, position and source trace.</p>
        <div className="heroActions">
          <a href="#catalogue" className="primary">Open catalogue</a>
          <button onClick={exportCsv}>Export current selection</button>
        </div>
      </div>
      <div className="qualityCard">
        <span>VIN workflow target</span>
        <strong>LGFP7AJJ7SA606343</strong>
        <p>Exact OE must always be final-confirmed by VIN/chassis, facelift, LHD/RHD, position and supplier photo. The platform refuses fake “all-fit” claims.</p>
      </div>
    </section>

    <section className="metrics">
      <Metric label="Catalogue lines" value={stats.records.toLocaleString()} />
      <Metric label="Brands" value={stats.brands} />
      <Metric label="Brand/model pairs" value={stats.models} />
      <Metric label="OE/source refs" value={stats.confirmedOE.toLocaleString()} />
      <Metric label="High confidence" value={stats.highConfidence} />
      <Metric label="Supplier corroborated" value={stats.mediumConfidence.toLocaleString()} />
    </section>

    <section className="method">
      <div>
        <h2>Not a second-grade catalogue.</h2>
        <p>This is structured like a real parts intelligence system: source trace, confidence grading, vehicle compatibility notes, Moroccan RFQ questions and exportable buying data.</p>
      </div>
      <div className="methodGrid">
        <Badge title="No invented OEMs" text="Unconfirmed items stay marked as RFQ / verification required." />
        <Badge title="Source trace" text="Every row keeps source file and page/line evidence." />
        <Badge title="Buyer safe" text="VIN, photos, LHD, facelift and position checks are embedded." />
        <Badge title="Scalable" text="Ready to add engine, clutch, DPF/EGR and heavy-truck master data." />
      </div>
    </section>

    <section id="catalogue" className="catalogueShell">
      <aside className="filters">
        <h2>Catalogue control</h2>
        <label>Search OE / part / source<input value={q} onChange={e=>setQ(e.target.value)} placeholder="e.g. EM2E, bumper, BYD, HOWO" /></label>
        <label>Brand<select value={brand} onChange={e=>{setBrand(e.target.value);setModel('')}}><option value="">All brands</option>{brands.map(b=><option key={b}>{b}</option>)}</select></label>
        <label>Model<select value={model} onChange={e=>setModel(e.target.value)}><option value="">All models</option>{models.map(m=><option key={m}>{m}</option>)}</select></label>
        <label>Part system<select value={group} onChange={e=>setGroup(e.target.value)}><option value="">All groups</option>{requestedGroups.map(g=><option key={g}>{g}</option>)}</select></label>
        <label>Evidence grade<select value={grade} onChange={e=>setGrade(e.target.value)}><option value="">All grades</option><option value="3">A — direct source</option><option value="2">B — supplier/catalogue</option><option value="1">C — RFQ only</option></select></label>
        <div className="filterStats"><b>{filtered.length.toLocaleString()}</b> visible rows<br/><span>{quality.confirmed.toLocaleString()} with OE/source refs · {quality.low} RFQ only</span></div>
      </aside>
      <section className="results">
        <div className="resultsTop"><h2>Master catalogue</h2><p>{quality.high} A-grade · {quality.medium} B-grade · {quality.low} C-grade</p></div>
        <div className="tableWrap">
          <table>
            <thead><tr><th>Vehicle</th><th>System</th><th>Part</th><th>OE/OEM</th><th>Evidence</th></tr></thead>
            <tbody>{filtered.slice(0,650).map(r=><tr key={r.id} onClick={()=>setSelected(r)} className={selected?.id===r.id?'active':''}>
              <td><b>{r.brand}</b><span>{r.model}</span><small>{r.segment}</small></td>
              <td><b>{r.group}</b><span>{r.position || 'Position TBD'}</span></td>
              <td>{r.part}<small>{r.category}</small></td>
              <td><code>{r.oe || 'OEM not confirmed'}</code><small>{r.alt}</small></td>
              <td><Grade rank={r.gradeRank}/><small>{r.sourceLine}</small></td>
            </tr>)}</tbody>
          </table>
        </div>
        {filtered.length>650 && <p className="limit">Showing first 650 rows for speed. Refine filters or export CSV for full selection.</p>}
      </section>
      <aside className="detail">
        {selected && <>
          <p className="eyebrow">Selected part intelligence</p>
          <h2>{selected.brand} · {selected.model}</h2>
          <Grade rank={selected.gradeRank}/>
          <dl>
            <dt>Internal ID</dt><dd>{selected.id}</dd>
            <dt>Part group</dt><dd>{selected.group}</dd>
            <dt>Part description</dt><dd>{selected.part}</dd>
            <dt>Position</dt><dd>{selected.position || 'Confirm LH/RH / front/rear'}</dd>
            <dt>OE/OEM</dt><dd><code>{selected.oe || 'OEM not confirmed'}</code></dd>
            <dt>Supplier ref</dt><dd>{selected.alt || '—'}</dd>
            <dt>Source</dt><dd>{selected.sourceFile}<br/>{selected.sourceLine}</dd>
            <dt>Morocco compatibility</dt><dd>{selected.notes}</dd>
            <dt>Supplier RFQ question</dt><dd>{selected.supplierQuestion}</dd>
          </dl>
        </>}
      </aside>
    </section>
  </main>
}

function Metric({label,value}){ return <div className="metric"><strong>{value}</strong><span>{label}</span></div> }
function Badge({title,text}){ return <article><h3>{title}</h3><p>{text}</p></article> }
function Grade({rank}){ const label=rank===3?'A / OE direct':rank===2?'B / Corroborated':'C / RFQ only'; return <span className={`grade g${rank}`}>{label}</span> }

export default App
