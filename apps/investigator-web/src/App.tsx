import { useEffect, useState } from "react";
import { fetchWorkbenchData, WorkbenchData } from "./api";
import { CaseWorkspace } from "./CaseWorkspace";

export function App() {
  const [caseId, setCaseId] = useState("case_001");
  const [inputCaseId, setInputCaseId] = useState("case_001");
  const [workbenchData, setWorkbenchData] = useState<WorkbenchData | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isCancelled = false;

    async function loadData() {
      setIsLoading(true);
      setError(null);
      try {
        const res = await fetchWorkbenchData(caseId);
        if (!isCancelled) {
          if (res.success) {
            setWorkbenchData(res.data);
          } else {
            setError(res.error.message || "Failed to load case workbench");
            setWorkbenchData(null);
          }
        }
      } catch (err: unknown) {
        if (!isCancelled) {
          const msg = err instanceof Error ? err.message : "Network error fetching workbench";
          setError(msg);
          setWorkbenchData(null);
        }
      } finally {
        if (!isCancelled) {
          setIsLoading(false);
        }
      }
    }

    loadData();

    return () => {
      isCancelled = true;
    };
  }, [caseId]);

  return (
    <div style={{ minHeight: "100vh", backgroundColor: "#f1f5f9" }}>
      <nav
        style={{
          backgroundColor: "#0f172a",
          color: "#ffffff",
          padding: "12px 24px",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: "12px",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          <span
            style={{
              fontWeight: 700,
              fontSize: "18px",
              letterSpacing: "-0.5px",
            }}
          >
            Investigator Workbench
          </span>
          <span
            style={{
              fontSize: "12px",
              background: "#1e293b",
              padding: "2px 8px",
              borderRadius: "4px",
              color: "#94a3b8",
            }}
          >
            v0.2.0-beta
          </span>
        </div>

        <form
          onSubmit={(e) => {
            e.preventDefault();
            if (inputCaseId.trim()) {
              setCaseId(inputCaseId.trim());
            }
          }}
          style={{ display: "flex", gap: "8px" }}
        >
          <input
            type="text"
            value={inputCaseId}
            onChange={(e) => setInputCaseId(e.target.value)}
            placeholder="Enter Case ID (e.g. case_001)"
            aria-label="Case ID"
            style={{
              padding: "6px 12px",
              borderRadius: "4px",
              border: "1px solid #334155",
              backgroundColor: "#1e293b",
              color: "#ffffff",
              fontSize: "14px",
            }}
          />
          <button
            type="submit"
            style={{
              padding: "6px 14px",
              borderRadius: "4px",
              border: "none",
              backgroundColor: "#2563eb",
              color: "#ffffff",
              fontSize: "14px",
              fontWeight: 500,
              cursor: "pointer",
            }}
          >
            Load Case
          </button>
        </form>
      </nav>

      {error ? (
        <main style={{ padding: "24px", maxWidth: "800px", margin: "40px auto", textAlign: "center" }}>
          <div
            style={{
              background: "#fef2f2",
              border: "1px solid #fecaca",
              borderRadius: "8px",
              padding: "24px",
              color: "#991b1b",
            }}
          >
            <h2 style={{ margin: "0 0 8px 0", fontSize: "20px" }}>Error Loading Case: {caseId}</h2>
            <p style={{ margin: 0, fontSize: "14px" }}>{error}</p>
          </div>
        </main>
      ) : workbenchData ? (
        <CaseWorkspace
          workbenchData={workbenchData}
          isLoading={isLoading}
          error={null}
        />
      ) : (
        <main style={{ padding: "24px", maxWidth: "800px", margin: "40px auto", textAlign: "center" }}>
          <p style={{ color: "#64748b" }}>Loading case workbench...</p>
        </main>
      )}
    </div>
  );
}

export default App;
