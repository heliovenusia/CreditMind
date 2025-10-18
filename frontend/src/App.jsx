import React, { useState } from "react";

// Minimal, production-clean single-file demo for CreditMind
// Assumes backend at http://127.0.0.1:8000
// - Upload aa_payload.json, sms_dump.json, telecom_meta.json (as files)
// - Optional: bank_statement.csv
// - Click Score → shows decision, score, reasons, tips

export default function App() {
  const [aaFile, setAaFile] = useState(null);
  const [smsFile, setSmsFile] = useState(null);
  const [telFile, setTelFile] = useState(null);
  const [csvFile, setCsvFile] = useState(null);

  const [loading, setLoading] = useState(false);
  const [ingestionId, setIngestionId] = useState("");
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [baseUrl, setBaseUrl] = useState("http://127.0.0.1:8000");

  async function readText(file) {
    if (!file) return null;
    const text = await file.text();
    return text;
  }

  function decisionBadge(decision) {
    const color = decision === "APPROVE" ? "bg-green-100 text-green-800" : decision === "REVIEW" ? "bg-amber-100 text-amber-800" : "bg-red-100 text-red-800";
    return <span className={`px-3 py-1 rounded-full text-sm font-semibold ${color}`}>{decision}</span>;
  }

  function meter(score) {
    const pct = Math.max(0, Math.min(100, Math.round(score * 100)));
    return (
      <div className="w-full">
        <div className="flex justify-between text-sm mb-1"><span>Approval score</span><span>{pct}%</span></div>
        <div className="w-full h-3 bg-gray-200 rounded-full overflow-hidden">
          <div className={`h-3 rounded-full ${pct>=75?"bg-green-500":pct>=50?"bg-amber-500":"bg-red-500"}`} style={{width: pct+"%"}} />
        </div>
      </div>
    );
  }

  async function handleScore() {
    setError(""); setResult(null); setLoading(true);
    try {
      // Read files as text and wrap as JSON strings
      const aaText = await readText(aaFile);
      const smsText = await readText(smsFile);
      const telText = await readText(telFile);

      const payload = {
        aa_payload: aaText || null,
        sms_dump: smsText || null,
        telecom_meta: telText || null,
      };

      // If CSV present, send multipart; else send JSON POST
      let ingestionIdLocal = "";
      if (csvFile) {
        const form = new FormData();
        if (payload.aa_payload) form.append("aa_payload", payload.aa_payload);
        if (payload.sms_dump) form.append("sms_dump", payload.sms_dump);
        if (payload.telecom_meta) form.append("telecom_meta", payload.telecom_meta);
        form.append("bank_statement_csv", csvFile);
        const r = await fetch(`${baseUrl}/score/ingest`, { method: "POST", body: form });
        if (!r.ok) throw new Error(`Ingest failed: ${r.status}`);
        const j = await r.json();
        ingestionIdLocal = j.ingestion_id;
      } else {
        const r = await fetch(`${baseUrl}/score/ingest`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
        if (!r.ok) throw new Error(`Ingest failed: ${r.status}`);
        const j = await r.json();
        ingestionIdLocal = j.ingestion_id;
      }
      setIngestionId(ingestionIdLocal);

      const r2 = await fetch(`${baseUrl}/score/run`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ingestion_id: ingestionIdLocal }),
      });
      if (!r2.ok) throw new Error(`Run failed: ${r2.status}`);
      const j2 = await r2.json();
      setResult(j2);
    } catch (e) {
      setError(String(e.message || e));
    } finally {
      setLoading(false);
    }
  }

  async function handlePurge() {
    if (!ingestionId) return;
    try {
      await fetch(`${baseUrl}/score/raw/${ingestionId}`, { method: "DELETE" });
      alert("Raw artefacts deleted (kept derived features + consent)");
    } catch {}
  }

  return (
    <div className="min-h-screen bg-gray-50 py-10">
      <div className="max-w-3xl mx-auto p-6 bg-white rounded-2xl shadow">
        <h1 className="text-2xl font-bold mb-2">CreditMind – Explainable & Privacy‑Preserving Credit AI</h1>
        <p className="text-gray-600 mb-6">Consent-first scoring with AA + SMS + Telco summaries. Demo client.</p>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
          <label className="block">
            <span className="text-sm font-medium">AA Payload (aa_payload.json)</span>
            <input type="file" accept="application/json" onChange={e=>setAaFile(e.target.files[0]||null)} className="mt-1 block w-full"/>
          </label>
          <label className="block">
            <span className="text-sm font-medium">SMS Dump (sms_dump.json)</span>
            <input type="file" accept="application/json" onChange={e=>setSmsFile(e.target.files[0]||null)} className="mt-1 block w-full"/>
          </label>
          <label className="block">
            <span className="text-sm font-medium">Telco Summary (telecom_meta.json)</span>
            <input type="file" accept="application/json" onChange={e=>setTelFile(e.target.files[0]||null)} className="mt-1 block w-full"/>
          </label>
          <label className="block">
            <span className="text-sm font-medium">Bank Statement CSV (optional)</span>
            <input type="file" accept=".csv" onChange={e=>setCsvFile(e.target.files[0]||null)} className="mt-1 block w-full"/>
          </label>
        </div>

        <div className="flex items-center gap-3 mb-6">
          <input className="border rounded px-3 py-2 w-full" value={baseUrl} onChange={e=>setBaseUrl(e.target.value)} />
          <button onClick={handleScore} disabled={loading} className="px-4 py-2 rounded-xl bg-black text-white disabled:opacity-50">{loading?"Scoring…":"Score"}</button>
          <button onClick={handlePurge} disabled={!ingestionId} className="px-4 py-2 rounded-xl bg-gray-100">Purge raw</button>
        </div>

        {error && <div className="p-3 rounded bg-red-50 text-red-700 mb-4">{error}</div>}

        {result && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              {decisionBadge(result.decision)}
              <div className="text-sm text-gray-500">Ingestion: {ingestionId.slice(0,8)}…</div>
            </div>
            {meter(result.score)}

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="p-4 rounded-xl bg-gray-50">
                <h3 className="font-semibold mb-2">Top reasons</h3>
                <ul className="list-disc ml-5 text-sm text-gray-700">
                  {result.reason_codes.map((r, i)=> <li key={i}>{r}</li>)}
                </ul>
              </div>
              <div className="p-4 rounded-xl bg-gray-50">
                <h3 className="font-semibold mb-2">Coach tips</h3>
                <ul className="list-disc ml-5 text-sm text-gray-700">
                  {result.coach_tips.map((t, i)=> <li key={i}>{t}</li>)}
                </ul>
              </div>
            </div>

            <details className="mt-2">
              <summary className="cursor-pointer text-sm text-gray-600">SHAP summary (raw)</summary>
              <pre className="text-xs overflow-x-auto bg-white p-3 rounded border">{JSON.stringify(result.shap_summary, null, 2)}</pre>
            </details>
          </div>
        )}

        <div className="mt-8 text-xs text-gray-500">Privacy: This demo stores only derived features + consent artefact. Use the Purge button to remove raw uploads immediately.</div>
      </div>
    </div>
  );
}
