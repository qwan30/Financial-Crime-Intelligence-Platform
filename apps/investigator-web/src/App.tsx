import { useEffect, useState } from "react";
import { fetchWorkbenchData, WorkbenchData } from "./api";
import { CaseWorkspace } from "./CaseWorkspace";

export function App() {
  const [caseId, setCaseId] = useState("canvas_vn_01");
  const [inputCaseId, setInputCaseId] = useState("canvas_vn_01");
  const [workbenchData, setWorkbenchData] = useState<WorkbenchData | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    setIsLoading(true);
    setError(null);
    setWorkbenchData(null); // Clear stale payload on load start

    fetchWorkbenchData(caseId, "", controller.signal)
      .then((res) => {
        if (res.success) {
          setWorkbenchData(res.data);
        } else {
          setError(res.error.message || "Failed to load case workbench");
        }
      })
      .catch((err: unknown) => {
        if (controller.signal.aborted) return;
        const msg = err instanceof Error ? err.message : "Unknown error";
        setError(msg);
      })
      .finally(() => {
        if (!controller.signal.aborted) {
          setIsLoading(false);
        }
      });

    return () => {
      controller.abort();
    };
  }, [caseId]);

  return (
    <div
      style={{
        display: "grid",
        gridTemplateRows: "auto minmax(0, 1fr)",
        height: "100dvh",
        width: "100vw",
        overflow: "hidden",
        backgroundColor: "#07090e",
        color: "#f8fafc",
        fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
      }}
    >
      {/* Navigation Header */}
      <nav
        style={{
          backgroundColor: "#0f172a",
          color: "#ffffff",
          padding: "10px 20px",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: "12px",
          borderBottom: "1px solid #1e293b",
          zIndex: 20,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          <span
            style={{
              fontWeight: 700,
              fontSize: "17px",
              letterSpacing: "-0.5px",
              color: "#38bdf8",
            }}
          >
            Investigator Workbench
          </span>
          <span
            style={{
              fontSize: "11px",
              background: "#1e293b",
              padding: "2px 8px",
              borderRadius: "4px",
              color: "#94a3b8",
            }}
          >
            Forensic Canvas v1.0
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
            placeholder="Mã vụ án (VD: canvas_vn_01)"
            aria-label="Case ID"
            style={{
              padding: "6px 12px",
              borderRadius: "4px",
              border: "1px solid #334155",
              backgroundColor: "#1e293b",
              color: "#ffffff",
              fontSize: "13px",
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
              fontSize: "13px",
              fontWeight: 600,
              cursor: "pointer",
            }}
          >
            Load Case
          </button>
        </form>
      </nav>

      {/* Workspace Area */}
      {error ? (
        <main
          style={{
            padding: "24px",
            maxWidth: "800px",
            margin: "40px auto",
            textAlign: "center",
          }}
        >
          <div
            style={{
              background: "#131b2e",
              border: "1px solid #f43f5e",
              borderRadius: "8px",
              padding: "24px",
            }}
          >
            <h3 style={{ color: "#f43f5e", margin: "0 0 8px 0" }}>
              Lỗi tải hồ sơ vụ án
            </h3>
            <p style={{ color: "#cbd5e1", margin: 0 }}>{error}</p>
          </div>
        </main>
      ) : workbenchData ? (
        <CaseWorkspace
          key={workbenchData.case.caseId}
          workbenchData={workbenchData}
        />
      ) : (
        <main
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            height: "100%",
            color: "#64748b",
          }}
        >
          <p>{isLoading ? "Đang tải dữ liệu hồ sơ..." : "Chưa tải vụ án"}</p>
        </main>
      )}
    </div>
  );
}

export default App;
