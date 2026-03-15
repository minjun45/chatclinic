"use client";

import { useMemo, useState } from "react";

type IntakeResponse = {
  source: {
    file_name: string;
    file_type: string;
    modality: string;
    size_bytes: number;
    status: string;
  };
  grounded_summary: string;
  studio_cards: Array<{ id: string; title: string; subtitle: string }>;
  artifacts: Record<string, unknown>;
};

type SchemaProfile = {
  name: string;
  inferred_type: string;
  non_empty_count: number;
  missing_count: number;
  missing_rate: number;
  unique_count: number;
  sample_values: string[];
  numeric_summary?: {
    min: number;
    max: number;
    mean: number;
  } | null;
};

type CohortArtifact = {
  record_count: number;
  field_count: number;
  categorical_breakdowns: Array<{
    column: string;
    top_values: Array<{ label: string; count: number }>;
  }>;
  numeric_breakdowns: Array<{
    column: string;
    summary: { min: number; max: number; mean: number } | null;
  }>;
};

export default function Page() {
  const [apiBase, setApiBase] = useState("http://127.0.0.1:8010");
  const [attachedFile, setAttachedFile] = useState<File | null>(null);
  const [status, setStatus] = useState("Waiting for a clinical source");
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<IntakeResponse | null>(null);
  const [chatTurns, setChatTurns] = useState<Array<{ role: "assistant" | "user"; content: string }>>([
    {
      role: "assistant",
      content:
        "Upload one clinical CSV/TSV file or one DICOM file. ChatClinic will generate a deterministic first-pass summary and open the matching Studio cards.",
    },
  ]);
  const [composerText, setComposerText] = useState("");
  const [activeStudioView, setActiveStudioView] = useState<string | null>(null);

  async function handleFileChange(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0] ?? null;
    if (!file) {
      return;
    }
    setAttachedFile(file);
    setResult(null);
    setActiveStudioView(null);
    setError(null);
    setStatus("Uploading and parsing...");

    const formData = new FormData();
    formData.append("file", file);

    try {
      const response = await fetch(`${apiBase.replace(/\/$/, "")}/api/v1/intake/upload`, {
        method: "POST",
        body: formData,
      });
      if (!response.ok) {
        throw new Error(await response.text());
      }
      const payload: IntakeResponse = await response.json();
      setResult(payload);
      setStatus("Summary ready");
      setChatTurns((current) => [
        current[0],
        {
          role: "assistant",
          content: payload.grounded_summary,
        },
      ]);
    } catch (caught) {
      const message = caught instanceof Error ? caught.message : String(caught);
      setError(message);
      setStatus("Upload failed");
    } finally {
      event.target.value = "";
    }
  }

  async function handleChatSubmit() {
    const text = composerText.trim();
    if (!text) {
      return;
    }

    if (!result) {
      setChatTurns((current) => [
        ...current,
        { role: "user", content: text },
        {
          role: "assistant",
          content: "Upload a clinical source first so ChatClinic has deterministic artifacts to explain.",
        },
      ]);
      setComposerText("");
      return;
    }

    setStatus("Answering...");
    setChatTurns((current) => [...current, { role: "user", content: text }]);
    setComposerText("");
    try {
      const response = await fetch(`${apiBase.replace(/\/$/, "")}/api/v1/chat/artifacts`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          question: text,
          analysis: result,
          history: chatTurns,
          active_view: activeStudioView,
        }),
      });
      if (!response.ok) {
        throw new Error(await response.text());
      }
      const payload = await response.json();
      setChatTurns((current) => [...current, { role: "assistant", content: payload.answer }]);
      setStatus("Summary ready");
    } catch (caught) {
      const message = caught instanceof Error ? caught.message : String(caught);
      setChatTurns((current) => [
        ...current,
        { role: "assistant", content: `Chat request failed: ${message}` },
      ]);
      setStatus("Answer failed");
    }
  }

  const studioArtifacts = useMemo(() => {
    if (!result || !activeStudioView) {
      return null;
    }
    return result.artifacts[activeStudioView] ?? null;
  }, [activeStudioView, result]);

  function renderStudioCanvas() {
    if (!result || !activeStudioView) {
      return <p className="mutedText">Upload a source, then open a Studio card to inspect deterministic artifacts.</p>;
    }

    if (activeStudioView === "schema") {
      const schema = (result.artifacts.schema as { profiles?: SchemaProfile[] } | undefined)?.profiles ?? [];
      return (
        <div className="artifactStack">
          {schema.map((profile) => (
            <article key={profile.name} className="artifactCard">
              <strong>
                {profile.name} <span className="artifactType">{profile.inferred_type}</span>
              </strong>
              <p>
                Non-empty {profile.non_empty_count} | Missing {profile.missing_count} | Unique {profile.unique_count}
              </p>
              <p>Sample values: {profile.sample_values.length ? profile.sample_values.join(", ") : "n/a"}</p>
              {profile.numeric_summary ? (
                <p>
                  Range {profile.numeric_summary.min} to {profile.numeric_summary.max} | Mean {profile.numeric_summary.mean}
                </p>
              ) : null}
            </article>
          ))}
        </div>
      );
    }

    if (activeStudioView === "cohort") {
      const cohort = result.artifacts.cohort as CohortArtifact | undefined;
      if (!cohort) {
        return <p className="mutedText">No cohort summary is available.</p>;
      }
      return (
        <div className="artifactStack">
          <article className="artifactCard">
            <strong>Cohort overview</strong>
            <p>Records: {cohort.record_count}</p>
            <p>Fields: {cohort.field_count}</p>
          </article>
          {cohort.categorical_breakdowns.map((item) => (
            <article key={item.column} className="artifactCard">
              <strong>{item.column}</strong>
              <ul className="artifactList">
                {item.top_values.map((entry) => (
                  <li key={`${item.column}-${entry.label}`}>
                    {entry.label}: {entry.count}
                  </li>
                ))}
              </ul>
            </article>
          ))}
          {cohort.numeric_breakdowns.map((item) => (
            <article key={item.column} className="artifactCard">
              <strong>{item.column}</strong>
              <p>
                Min {item.summary?.min ?? "n/a"} | Max {item.summary?.max ?? "n/a"} | Mean {item.summary?.mean ?? "n/a"}
              </p>
            </article>
          ))}
        </div>
      );
    }

    return studioArtifacts ? <pre>{JSON.stringify(studioArtifacts, null, 2)}</pre> : null;
  }

  return (
    <main className="shell">
      <header className="topbar">
        <div className="brand">ChatClinic</div>
        <div className="copyright">Clinical data and imaging workspace scaffold</div>
      </header>
      <div className="grid">
        <section className="panel">
          <h2>Sources</h2>
          <label className="uploadButton">
            + Add clinical source
            <input type="file" accept=".csv,.tsv,.dcm,.dicom" onChange={handleFileChange} />
          </label>
          <label className="fieldLabel">
            API base URL
            <input value={apiBase} onChange={(event) => setApiBase(event.target.value)} className="textInput" />
          </label>
          {attachedFile ? (
            <article className="sourceCard">
              <strong>{attachedFile.name}</strong>
              <span>{result?.source.modality ?? "pending"}</span>
            </article>
          ) : (
            <p className="mutedText">Attach a CSV/TSV clinical table or a DICOM file.</p>
          )}
          <div className="statusBlock">
            <span>Status</span>
            <strong>{status}</strong>
          </div>
          {error ? <p className="errorText">{error}</p> : null}
        </section>

        <section className="panel">
          <div className="chatHeader">
            <h2>Chat</h2>
            <span className="statusPill">{status}</span>
          </div>
          <div className="chatStream">
            {chatTurns.map((turn, index) => (
              <article key={`turn-${index}`} className={turn.role === "user" ? "userBubble" : "assistantBlock"}>
                <p>{turn.content}</p>
              </article>
            ))}
          </div>
          <div className="chatComposer">
            <input
              value={composerText}
              onChange={(event) => setComposerText(event.target.value)}
              placeholder="Ask a follow-up question about the current scaffold..."
              className="chatInput"
            />
            <button type="button" className="sendButton" onClick={handleChatSubmit}>
              →
            </button>
          </div>
        </section>

        <section className="panel">
          <h2>Studio</h2>
          <div className="studioGrid">
            {(result?.studio_cards ?? [
              { id: "qc", title: "Clinical QC", subtitle: "Rows, columns, completeness" },
              { id: "schema", title: "Schema Review", subtitle: "Detected variables" },
              { id: "metadata", title: "Imaging Metadata", subtitle: "DICOM tags and identifiers" },
              { id: "report", title: "Report Draft", subtitle: "Grounded summary draft" },
            ]).map((card) => (
              <button
                key={card.id}
                type="button"
                className={`studioCard ${activeStudioView === card.id ? "studioCardActive" : ""}`}
                onClick={() => setActiveStudioView(card.id)}
                disabled={!result}
              >
                <strong>{card.title}</strong>
                <span>{card.subtitle}</span>
              </button>
            ))}
          </div>
          <div className="studioCanvas">
            {renderStudioCanvas()}
          </div>
        </section>
      </div>
    </main>
  );
}
