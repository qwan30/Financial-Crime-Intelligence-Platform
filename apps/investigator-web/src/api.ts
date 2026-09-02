export type ErrorDetail = {
  code: string;
  message: string;
};

export type SuccessEnvelope<T> = {
  success: true;
  data: T;
  error: null;
};

export type ErrorEnvelope = {
  success: false;
  data: null;
  error: ErrorDetail;
};

export type CaseResponse = {
  caseId: string;
  seedEntity: string;
  evidenceIds: string[];
  traceEdgeIds: string[];
  createdAt: string;
  snapshotHash: string;
};

export type EvidencePolarity =
  | "SUPPORTING"
  | "MITIGATING"
  | "MISSING"
  | "UNKNOWN";

export type EvidenceCategory =
  | "OBSERVED"
  | "DERIVED"
  | "RULE"
  | "MODEL"
  | "TRACE"
  | "ANALYST";

export type EvidenceResponse = {
  evidenceId: string;
  category: string;
  sourceReference: string;
  polarity: string;
  snapshotTime: string;
  generationMethodVersion: string;
  payloadSummary: string;
  integrityHash: string;
  confidence?: number | null;
};

export type TraceNodeResponse = {
  nodeId: string;
  entityType: string;
  riskScore?: number | null;
  isSeed: boolean;
  isContext: boolean;
};

export type TraceEdgeResponse = {
  edgeId: string;
  source: string;
  target: string;
  flowAmount: number;
  relationshipType: string;
  identityConfidence: number;
};

export type TraceGraphResponse = {
  nodes: TraceNodeResponse[];
  edges: TraceEdgeResponse[];
  isTruncated: boolean;
  totalHops: number;
};

export type MaterialClaimResponse = {
  claimText: string;
  citedEvidenceIds: string[];
};

export type HypothesisStatus =
  | "HYPOTHESIS_GENERATED"
  | "INSUFFICIENT_EVIDENCE"
  | "AI_UNAVAILABLE"
  | "AI_INVALID_OUTPUT";

export type HypothesisResponse = {
  hypothesisId: string;
  caseId: string;
  status: string;
  summary: string;
  claims: MaterialClaimResponse[];
  generatedAt: string;
  modelVersion?: string | null;
};

export type WorkbenchData = {
  case: CaseResponse;
  evidence: EvidenceResponse[];
  trace: TraceGraphResponse;
  hypothesis: HypothesisResponse;
};

export type Disposition =
  | "CONFIRMED_SUSPICIOUS"
  | "FALSE_POSITIVE"
  | "ESCALATE"
  | "INSUFFICIENT_EVIDENCE";

export type AdjudicationStatus = "PENDING" | "ACCEPTED" | "REJECTED";

export type FeedbackRequest = {
  eventId: string;
  analystId: string;
  disposition: Disposition;
  reason: string;
  createdAt: string;
  modelVersion?: string | null;
  snapshotHash: string;
  adjudicationStatus?: AdjudicationStatus;
};

export type CaseEnvelope = SuccessEnvelope<CaseResponse> | ErrorEnvelope;
export type WorkbenchEnvelope = SuccessEnvelope<WorkbenchData> | ErrorEnvelope;
export type FeedbackEnvelope =
  | SuccessEnvelope<Record<string, unknown>>
  | ErrorEnvelope;

export async function fetchWorkbenchData(
  caseId: string,
  baseUrl = ""
): Promise<WorkbenchEnvelope> {
  try {
    const res = await fetch(
      `${baseUrl}/cases/${encodeURIComponent(caseId)}/workbench`
    );
    const json = await res.json();
    return json as WorkbenchEnvelope;
  } catch (err: unknown) {
    const message =
      err instanceof Error ? err.message : "Network error fetching workbench data";
    return {
      success: false,
      data: null,
      error: {
        code: "FETCH_ERROR",
        message,
      },
    };
  }
}

export async function fetchCase(
  caseId: string,
  baseUrl = ""
): Promise<CaseEnvelope> {
  try {
    const res = await fetch(
      `${baseUrl}/cases/${encodeURIComponent(caseId)}`
    );
    const json = await res.json();
    return json as CaseEnvelope;
  } catch (err: unknown) {
    const message =
      err instanceof Error ? err.message : "Network error fetching case";
    return {
      success: false,
      data: null,
      error: {
        code: "FETCH_ERROR",
        message,
      },
    };
  }
}

export async function submitFeedback(
  caseId: string,
  feedback: FeedbackRequest,
  baseUrl = ""
): Promise<FeedbackEnvelope> {
  try {
    const res = await fetch(
      `${baseUrl}/cases/${encodeURIComponent(caseId)}/feedback`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(feedback),
      }
    );
    const json = await res.json();
    return json as FeedbackEnvelope;
  } catch (err: unknown) {
    const message =
      err instanceof Error ? err.message : "Network error submitting feedback";
    return {
      success: false,
      data: null,
      error: {
        code: "SUBMIT_FEEDBACK_ERROR",
        message,
      },
    };
  }
}
