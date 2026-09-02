import { test, expect } from "@playwright/test";

const mockWorkbenchData = {
  success: true,
  data: {
    case: {
      caseId: "case_001",
      seedEntity: "account:case_001",
      evidenceIds: ["ev_001", "ev_002", "ev_003"],
      traceEdgeIds: ["e_001", "e_002"],
      createdAt: "2026-03-01T12:00:00Z",
      snapshotHash: "4f8a9b2c1d3e5f7a6b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a",
    },
    evidence: [
      {
        evidenceId: "ev_001",
        category: "OBSERVED",
        sourceReference: "tx-1001",
        polarity: "SUPPORTING",
        snapshotTime: "2026-03-01T10:00:00Z",
        generationMethodVersion: "v1.0.0",
        payloadSummary: "Structured cash deposit of $9,500 across 3 ATM locations",
        integrityHash: "1111111111111111111111111111111111111111111111111111111111111111",
        confidence: 0.95,
      },
      {
        evidenceId: "ev_002",
        category: "RULE",
        sourceReference: "rule-threshold-04",
        polarity: "SUPPORTING",
        snapshotTime: "2026-03-01T10:30:00Z",
        generationMethodVersion: "v1.0.0",
        payloadSummary: "Velocity threshold violation: 4 outbound transfers within 30 minutes",
        integrityHash: "2222222222222222222222222222222222222222222222222222222222222222",
        confidence: 0.88,
      },
      {
        evidenceId: "ev_003",
        category: "ANALYST",
        sourceReference: "kyc-profile-acc01",
        polarity: "MITIGATING",
        snapshotTime: "2026-03-01T11:00:00Z",
        generationMethodVersion: "v1.0.0",
        payloadSummary: "Verified corporate payroll account with consistent seasonal volume",
        integrityHash: "3333333333333333333333333333333333333333333333333333333333333333",
        confidence: 0.75,
      },
    ],
    trace: {
      nodes: [
        {
          nodeId: "account:case_001",
          entityType: "ACCOUNT",
          riskScore: 0.85,
          isSeed: true,
          isContext: false,
        },
        {
          nodeId: "account:dest_mule_01",
          entityType: "ACCOUNT",
          riskScore: 0.72,
          isSeed: false,
          isContext: false,
        },
        {
          nodeId: "account:context_bank_hq",
          entityType: "BRANCH",
          riskScore: 0.15,
          isSeed: false,
          isContext: true,
        },
      ],
      edges: [
        {
          edgeId: "e_001",
          source: "account:case_001",
          target: "account:dest_mule_01",
          flowAmount: 28500,
          relationshipType: "WIRE_TRANSFER",
          identityConfidence: 0.92,
        },
        {
          edgeId: "e_002",
          source: "account:dest_mule_01",
          target: "account:context_bank_hq",
          flowAmount: 5000,
          relationshipType: "SETTLEMENT",
          identityConfidence: 0.65,
        },
      ],
      isTruncated: false,
      totalHops: 2,
    },
    hypothesis: {
      hypothesisId: "hypo-case_001",
      caseId: "case_001",
      status: "HYPOTHESIS_GENERATED",
      summary: "Automated reasoning detected high-probability money muling coordination. Rapid structuring deposits funnel into account:dest_mule_01 before partial outbound settlement.",
      claims: [
        {
          claimText: "Repeated structured deposits immediately precede outbound wire transfers.",
          citedEvidenceIds: ["ev_001", "ev_002"],
        },
        {
          claimText: "Verified corporate identity partially mitigates branch settlement anomalies.",
          citedEvidenceIds: ["ev_003"],
        },
      ],
      generatedAt: "2026-03-01T12:05:00Z",
      modelVersion: "deepseek-v4-flash",
    },
  },
  error: null,
};

test.describe("Investigator Workbench E2E User Journey", () => {
  test.beforeEach(async ({ page }) => {
    // Intercept workbench API calls
    await page.route("**/cases/**/workbench", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(mockWorkbenchData),
      });
    });

    // Intercept feedback API calls
    await page.route("**/cases/**/feedback", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: { status: "accepted", eventId: "fb-test-001" },
          error: null,
        }),
      });
    });
  });

  test("loads case workspace with evidence timeline, graph container, and AI hypothesis", async ({ page }) => {
    await page.goto("/");

    // 1. Verify App navigation and Case header
    await expect(page.locator("text=Investigator Workbench")).toBeVisible();
    await expect(page.locator("text=Seed Entity:")).toBeVisible();
    await expect(page.locator("text=account:case_001")).toBeVisible();

    // 2. Verify Evidence Timeline section and items
    await expect(page.locator("h2:has-text('Evidence Timeline')")).toBeVisible();
    await expect(page.locator("text=Structured cash deposit of $9,500 across 3 ATM locations")).toBeVisible();
    await expect(page.locator("text=SUPPORTING").first()).toBeVisible();
    await expect(page.locator("text=MITIGATING").first()).toBeVisible();

    // 3. Verify Graph Visualization Container
    await expect(page.locator("[data-testid='trace-graph-container']")).toBeVisible();

    // 4. Verify AI Hypothesis Panel and Claims
    await expect(page.locator("h2:has-text('AI Investigation Hypothesis')")).toBeVisible();
    await expect(page.locator("text=HYPOTHESIS_GENERATED")).toBeVisible();
    await expect(page.locator("text=Repeated structured deposits immediately precede outbound wire transfers.")).toBeVisible();

    // 5. Verify Analyst Feedback Action Panel
    await expect(page.locator("h2:has-text('Analyst Adjudication & Feedback')")).toBeVisible();
    await expect(page.locator("button:has-text('Submit Disposition')")).toBeVisible();
  });

  test("allows analyst to select disposition, enter justification, and submit feedback", async ({ page }) => {
    await page.goto("/");

    // Select ESCALATE disposition from select combobox
    const select = page.locator("select, [aria-label='Case Disposition']");
    await expect(select).toBeVisible();
    await select.selectOption("ESCALATE");

    // Fill reasoning
    const textarea = page.locator("textarea, [aria-label='Adjudication Rationale']");
    await textarea.fill("High-velocity fund layering across multiple accounts requires AML escalation.");

    // Submit feedback
    const submitBtn = page.locator("button:has-text('Submit Disposition')");
    await expect(submitBtn).toBeEnabled();
    await submitBtn.click();

    // Verify submission feedback
    await expect(page.locator("text=Feedback submitted successfully")).toBeVisible({ timeout: 5000 });
  });
});
