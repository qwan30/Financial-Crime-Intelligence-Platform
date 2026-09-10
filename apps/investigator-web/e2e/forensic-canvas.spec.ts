import { expect, test } from "@playwright/test";

const traces = {
  "initial": {
    "nodes": [
      {
        "nodeId": "evn",
        "entityType": "ACCOUNT",
        "riskScore": 0.08,
        "isSeed": false,
        "isContext": true,
        "accountHolderName": "Tổng công ty Điện lực Thành phố Hồ Chí Minh",
        "bankShortName": "Vietcombank",
        "accountLast4": "1100",
        "badge": "BENIGN"
      },
      {
        "nodeId": "hub",
        "entityType": "ACCOUNT",
        "riskScore": 0.88,
        "isSeed": true,
        "isContext": false,
        "accountHolderName": "Nguyễn Văn A",
        "bankShortName": "Vietcombank",
        "accountLast4": "2891",
        "badge": "SEED_HUB"
      },
      {
        "nodeId": "mule1",
        "entityType": "ACCOUNT",
        "riskScore": 0.76,
        "isSeed": false,
        "isContext": false,
        "accountHolderName": "Trần Thị Bình",
        "bankShortName": "Sacombank",
        "accountLast4": "9020",
        "badge": "SMURFING"
      },
      {
        "nodeId": "mule2",
        "entityType": "ACCOUNT",
        "riskScore": 0.72,
        "isSeed": false,
        "isContext": false,
        "accountHolderName": "Lê Văn Cường",
        "bankShortName": "BIDV",
        "accountLast4": "4812",
        "badge": "SMURFING"
      },
      {
        "nodeId": "mule3",
        "entityType": "ACCOUNT",
        "riskScore": 0.67,
        "isSeed": false,
        "isContext": false,
        "accountHolderName": "Phạm Thị Dung",
        "bankShortName": "VietinBank",
        "accountLast4": "3510",
        "badge": "SMURFING"
      },
      {
        "nodeId": "mule4",
        "entityType": "ACCOUNT",
        "riskScore": 0.64,
        "isSeed": false,
        "isContext": false,
        "accountHolderName": "Hoàng Văn Em",
        "bankShortName": "Techcombank",
        "accountLast4": "1164",
        "badge": "SMURFING"
      },
      {
        "nodeId": "mule5",
        "entityType": "ACCOUNT",
        "riskScore": 0.62,
        "isSeed": false,
        "isContext": false,
        "accountHolderName": "Vũ Thị Phương",
        "bankShortName": "ACB",
        "accountLast4": "7701",
        "badge": "SMURFING"
      },
      {
        "nodeId": "shell",
        "entityType": "COMPANY",
        "riskScore": 0.92,
        "isSeed": false,
        "isContext": false,
        "accountHolderName": "Công ty TNHH Thương mại và Dịch vụ Nam Phát",
        "bankShortName": "Techcombank",
        "accountLast4": "0012",
        "badge": "SHELL_CORP"
      }
    ],
    "edges": [
      {
        "edgeId": "TXN-2026-8800",
        "source": "hub",
        "target": "evn",
        "flowAmount": 1500000.0,
        "relationshipType": "NAPAS_247",
        "identityConfidence": 0.98,
        "currency": "VND",
        "timestamp": "2026-09-08T01:15:00Z"
      },
      {
        "edgeId": "TXN-2026-8801",
        "source": "mule1",
        "target": "hub",
        "flowAmount": 10000000.0,
        "relationshipType": "NAPAS_247",
        "identityConfidence": 0.98,
        "currency": "VND",
        "timestamp": "2026-09-08T01:30:00Z"
      },
      {
        "edgeId": "TXN-2026-8802",
        "source": "mule2",
        "target": "hub",
        "flowAmount": 25000000.0,
        "relationshipType": "NAPAS_247",
        "identityConfidence": 0.98,
        "currency": "VND",
        "timestamp": "2026-09-08T01:40:00Z"
      },
      {
        "edgeId": "TXN-2026-8803",
        "source": "mule3",
        "target": "hub",
        "flowAmount": 45000000.0,
        "relationshipType": "NAPAS_247",
        "identityConfidence": 0.98,
        "currency": "VND",
        "timestamp": "2026-09-08T01:55:00Z"
      },
      {
        "edgeId": "TXN-2026-8804",
        "source": "hub",
        "target": "shell",
        "flowAmount": 140000000.0,
        "relationshipType": "NAPAS_247",
        "identityConfidence": 0.98,
        "currency": "VND",
        "timestamp": "2026-09-08T02:12:00Z"
      },
      {
        "edgeId": "TXN-2026-8808",
        "source": "mule4",
        "target": "hub",
        "flowAmount": 20000000.0,
        "relationshipType": "NAPAS_247",
        "identityConfidence": 0.98,
        "currency": "VND",
        "timestamp": "2026-09-08T02:00:00Z"
      },
      {
        "edgeId": "TXN-2026-8809",
        "source": "mule5",
        "target": "hub",
        "flowAmount": 30000000.0,
        "relationshipType": "NAPAS_247",
        "identityConfidence": 0.98,
        "currency": "VND",
        "timestamp": "2026-09-08T02:05:00Z"
      }
    ],
    "isTruncated": true,
    "totalHops": 1,
    "hopByNodeId": {
      "mule4": 1,
      "shell": 1,
      "mule3": 1,
      "hub": 0,
      "mule2": 1,
      "evn": 1,
      "mule1": 1,
      "mule5": 1
    },
    "timeMin": "2026-09-08T01:15:00+00:00",
    "timeMax": "2026-09-08T02:55:00+00:00",
    "unknownTimeEdgeCount": 0
  },
  "expandShell": {
    "nodes": [
      {
        "nodeId": "atm",
        "entityType": "ATM",
        "riskScore": 0.86,
        "isSeed": false,
        "isContext": false,
        "accountHolderName": "Cây ATM Vietcombank Quận 1",
        "bankShortName": "Vietcombank",
        "accountLast4": null,
        "badge": "CASHOUT"
      },
      {
        "nodeId": "crypto",
        "entityType": "ACCOUNT",
        "riskScore": 0.89,
        "isSeed": false,
        "isContext": false,
        "accountHolderName": "Đại lý giao dịch P2P tài sản mã hóa",
        "bankShortName": null,
        "accountLast4": null,
        "badge": "CRYPTO_OTC"
      },
      {
        "nodeId": "evn",
        "entityType": "ACCOUNT",
        "riskScore": 0.08,
        "isSeed": false,
        "isContext": true,
        "accountHolderName": "Tổng công ty Điện lực Thành phố Hồ Chí Minh",
        "bankShortName": "Vietcombank",
        "accountLast4": "1100",
        "badge": "BENIGN"
      },
      {
        "nodeId": "hub",
        "entityType": "ACCOUNT",
        "riskScore": 0.88,
        "isSeed": true,
        "isContext": false,
        "accountHolderName": "Nguyễn Văn A",
        "bankShortName": "Vietcombank",
        "accountLast4": "2891",
        "badge": "SEED_HUB"
      },
      {
        "nodeId": "mule1",
        "entityType": "ACCOUNT",
        "riskScore": 0.76,
        "isSeed": false,
        "isContext": false,
        "accountHolderName": "Trần Thị Bình",
        "bankShortName": "Sacombank",
        "accountLast4": "9020",
        "badge": "SMURFING"
      },
      {
        "nodeId": "mule2",
        "entityType": "ACCOUNT",
        "riskScore": 0.72,
        "isSeed": false,
        "isContext": false,
        "accountHolderName": "Lê Văn Cường",
        "bankShortName": "BIDV",
        "accountLast4": "4812",
        "badge": "SMURFING"
      },
      {
        "nodeId": "mule3",
        "entityType": "ACCOUNT",
        "riskScore": 0.67,
        "isSeed": false,
        "isContext": false,
        "accountHolderName": "Phạm Thị Dung",
        "bankShortName": "VietinBank",
        "accountLast4": "3510",
        "badge": "SMURFING"
      },
      {
        "nodeId": "mule4",
        "entityType": "ACCOUNT",
        "riskScore": 0.64,
        "isSeed": false,
        "isContext": false,
        "accountHolderName": "Hoàng Văn Em",
        "bankShortName": "Techcombank",
        "accountLast4": "1164",
        "badge": "SMURFING"
      },
      {
        "nodeId": "mule5",
        "entityType": "ACCOUNT",
        "riskScore": 0.62,
        "isSeed": false,
        "isContext": false,
        "accountHolderName": "Vũ Thị Phương",
        "bankShortName": "ACB",
        "accountLast4": "7701",
        "badge": "SMURFING"
      },
      {
        "nodeId": "shell",
        "entityType": "COMPANY",
        "riskScore": 0.92,
        "isSeed": false,
        "isContext": false,
        "accountHolderName": "Công ty TNHH Thương mại và Dịch vụ Nam Phát",
        "bankShortName": "Techcombank",
        "accountLast4": "0012",
        "badge": "SHELL_CORP"
      }
    ],
    "edges": [
      {
        "edgeId": "TXN-2026-8800",
        "source": "hub",
        "target": "evn",
        "flowAmount": 1500000.0,
        "relationshipType": "NAPAS_247",
        "identityConfidence": 0.98,
        "currency": "VND",
        "timestamp": "2026-09-08T01:15:00Z"
      },
      {
        "edgeId": "TXN-2026-8801",
        "source": "mule1",
        "target": "hub",
        "flowAmount": 10000000.0,
        "relationshipType": "NAPAS_247",
        "identityConfidence": 0.98,
        "currency": "VND",
        "timestamp": "2026-09-08T01:30:00Z"
      },
      {
        "edgeId": "TXN-2026-8802",
        "source": "mule2",
        "target": "hub",
        "flowAmount": 25000000.0,
        "relationshipType": "NAPAS_247",
        "identityConfidence": 0.98,
        "currency": "VND",
        "timestamp": "2026-09-08T01:40:00Z"
      },
      {
        "edgeId": "TXN-2026-8803",
        "source": "mule3",
        "target": "hub",
        "flowAmount": 45000000.0,
        "relationshipType": "NAPAS_247",
        "identityConfidence": 0.98,
        "currency": "VND",
        "timestamp": "2026-09-08T01:55:00Z"
      },
      {
        "edgeId": "TXN-2026-8804",
        "source": "hub",
        "target": "shell",
        "flowAmount": 140000000.0,
        "relationshipType": "NAPAS_247",
        "identityConfidence": 0.98,
        "currency": "VND",
        "timestamp": "2026-09-08T02:12:00Z"
      },
      {
        "edgeId": "TXN-2026-8805",
        "source": "shell",
        "target": "atm",
        "flowAmount": 60000000.0,
        "relationshipType": "NAPAS_247",
        "identityConfidence": 0.98,
        "currency": "VND",
        "timestamp": "2026-09-08T02:35:00Z"
      },
      {
        "edgeId": "TXN-2026-8806",
        "source": "shell",
        "target": "crypto",
        "flowAmount": 80000000.0,
        "relationshipType": "NAPAS_247",
        "identityConfidence": 0.98,
        "currency": "VND",
        "timestamp": "2026-09-08T02:50:00Z"
      },
      {
        "edgeId": "TXN-2026-8808",
        "source": "mule4",
        "target": "hub",
        "flowAmount": 20000000.0,
        "relationshipType": "NAPAS_247",
        "identityConfidence": 0.98,
        "currency": "VND",
        "timestamp": "2026-09-08T02:00:00Z"
      },
      {
        "edgeId": "TXN-2026-8809",
        "source": "mule5",
        "target": "hub",
        "flowAmount": 30000000.0,
        "relationshipType": "NAPAS_247",
        "identityConfidence": 0.98,
        "currency": "VND",
        "timestamp": "2026-09-08T02:05:00Z"
      }
    ],
    "isTruncated": true,
    "totalHops": 2,
    "hopByNodeId": {
      "atm": 2,
      "mule4": 1,
      "shell": 1,
      "mule3": 1,
      "hub": 0,
      "mule2": 1,
      "crypto": 2,
      "evn": 1,
      "mule1": 1,
      "mule5": 1
    },
    "timeMin": "2026-09-08T01:15:00+00:00",
    "timeMax": "2026-09-08T02:55:00+00:00",
    "unknownTimeEdgeCount": 0
  },
  "expandAtm": {
    "nodes": [
      {
        "nodeId": "atm",
        "entityType": "ATM",
        "riskScore": 0.86,
        "isSeed": false,
        "isContext": false,
        "accountHolderName": "Cây ATM Vietcombank Quận 1",
        "bankShortName": "Vietcombank",
        "accountLast4": null,
        "badge": "CASHOUT"
      },
      {
        "nodeId": "crypto",
        "entityType": "ACCOUNT",
        "riskScore": 0.89,
        "isSeed": false,
        "isContext": false,
        "accountHolderName": "Đại lý giao dịch P2P tài sản mã hóa",
        "bankShortName": null,
        "accountLast4": null,
        "badge": "CRYPTO_OTC"
      },
      {
        "nodeId": "evn",
        "entityType": "ACCOUNT",
        "riskScore": 0.08,
        "isSeed": false,
        "isContext": true,
        "accountHolderName": "Tổng công ty Điện lực Thành phố Hồ Chí Minh",
        "bankShortName": "Vietcombank",
        "accountLast4": "1100",
        "badge": "BENIGN"
      },
      {
        "nodeId": "exit3",
        "entityType": "ACCOUNT",
        "riskScore": 0.55,
        "isSeed": false,
        "isContext": false,
        "accountHolderName": "Tài khoản trung chuyển cấp ba",
        "bankShortName": "BIDV",
        "accountLast4": "9090",
        "badge": "LAYERING"
      },
      {
        "nodeId": "hub",
        "entityType": "ACCOUNT",
        "riskScore": 0.88,
        "isSeed": true,
        "isContext": false,
        "accountHolderName": "Nguyễn Văn A",
        "bankShortName": "Vietcombank",
        "accountLast4": "2891",
        "badge": "SEED_HUB"
      },
      {
        "nodeId": "mule1",
        "entityType": "ACCOUNT",
        "riskScore": 0.76,
        "isSeed": false,
        "isContext": false,
        "accountHolderName": "Trần Thị Bình",
        "bankShortName": "Sacombank",
        "accountLast4": "9020",
        "badge": "SMURFING"
      },
      {
        "nodeId": "mule2",
        "entityType": "ACCOUNT",
        "riskScore": 0.72,
        "isSeed": false,
        "isContext": false,
        "accountHolderName": "Lê Văn Cường",
        "bankShortName": "BIDV",
        "accountLast4": "4812",
        "badge": "SMURFING"
      },
      {
        "nodeId": "mule3",
        "entityType": "ACCOUNT",
        "riskScore": 0.67,
        "isSeed": false,
        "isContext": false,
        "accountHolderName": "Phạm Thị Dung",
        "bankShortName": "VietinBank",
        "accountLast4": "3510",
        "badge": "SMURFING"
      },
      {
        "nodeId": "mule4",
        "entityType": "ACCOUNT",
        "riskScore": 0.64,
        "isSeed": false,
        "isContext": false,
        "accountHolderName": "Hoàng Văn Em",
        "bankShortName": "Techcombank",
        "accountLast4": "1164",
        "badge": "SMURFING"
      },
      {
        "nodeId": "mule5",
        "entityType": "ACCOUNT",
        "riskScore": 0.62,
        "isSeed": false,
        "isContext": false,
        "accountHolderName": "Vũ Thị Phương",
        "bankShortName": "ACB",
        "accountLast4": "7701",
        "badge": "SMURFING"
      },
      {
        "nodeId": "shell",
        "entityType": "COMPANY",
        "riskScore": 0.92,
        "isSeed": false,
        "isContext": false,
        "accountHolderName": "Công ty TNHH Thương mại và Dịch vụ Nam Phát",
        "bankShortName": "Techcombank",
        "accountLast4": "0012",
        "badge": "SHELL_CORP"
      }
    ],
    "edges": [
      {
        "edgeId": "TXN-2026-8800",
        "source": "hub",
        "target": "evn",
        "flowAmount": 1500000.0,
        "relationshipType": "NAPAS_247",
        "identityConfidence": 0.98,
        "currency": "VND",
        "timestamp": "2026-09-08T01:15:00Z"
      },
      {
        "edgeId": "TXN-2026-8801",
        "source": "mule1",
        "target": "hub",
        "flowAmount": 10000000.0,
        "relationshipType": "NAPAS_247",
        "identityConfidence": 0.98,
        "currency": "VND",
        "timestamp": "2026-09-08T01:30:00Z"
      },
      {
        "edgeId": "TXN-2026-8802",
        "source": "mule2",
        "target": "hub",
        "flowAmount": 25000000.0,
        "relationshipType": "NAPAS_247",
        "identityConfidence": 0.98,
        "currency": "VND",
        "timestamp": "2026-09-08T01:40:00Z"
      },
      {
        "edgeId": "TXN-2026-8803",
        "source": "mule3",
        "target": "hub",
        "flowAmount": 45000000.0,
        "relationshipType": "NAPAS_247",
        "identityConfidence": 0.98,
        "currency": "VND",
        "timestamp": "2026-09-08T01:55:00Z"
      },
      {
        "edgeId": "TXN-2026-8804",
        "source": "hub",
        "target": "shell",
        "flowAmount": 140000000.0,
        "relationshipType": "NAPAS_247",
        "identityConfidence": 0.98,
        "currency": "VND",
        "timestamp": "2026-09-08T02:12:00Z"
      },
      {
        "edgeId": "TXN-2026-8805",
        "source": "shell",
        "target": "atm",
        "flowAmount": 60000000.0,
        "relationshipType": "NAPAS_247",
        "identityConfidence": 0.98,
        "currency": "VND",
        "timestamp": "2026-09-08T02:35:00Z"
      },
      {
        "edgeId": "TXN-2026-8806",
        "source": "shell",
        "target": "crypto",
        "flowAmount": 80000000.0,
        "relationshipType": "NAPAS_247",
        "identityConfidence": 0.98,
        "currency": "VND",
        "timestamp": "2026-09-08T02:50:00Z"
      },
      {
        "edgeId": "TXN-2026-8807",
        "source": "atm",
        "target": "exit3",
        "flowAmount": 10000000.0,
        "relationshipType": "NAPAS_247",
        "identityConfidence": 0.65,
        "currency": "VND",
        "timestamp": "2026-09-08T02:55:00Z"
      },
      {
        "edgeId": "TXN-2026-8808",
        "source": "mule4",
        "target": "hub",
        "flowAmount": 20000000.0,
        "relationshipType": "NAPAS_247",
        "identityConfidence": 0.98,
        "currency": "VND",
        "timestamp": "2026-09-08T02:00:00Z"
      },
      {
        "edgeId": "TXN-2026-8809",
        "source": "mule5",
        "target": "hub",
        "flowAmount": 30000000.0,
        "relationshipType": "NAPAS_247",
        "identityConfidence": 0.98,
        "currency": "VND",
        "timestamp": "2026-09-08T02:05:00Z"
      }
    ],
    "isTruncated": false,
    "totalHops": 3,
    "hopByNodeId": {
      "mule4": 1,
      "mule5": 1,
      "shell": 1,
      "exit3": 3,
      "mule3": 1,
      "hub": 0,
      "mule2": 1,
      "crypto": 2,
      "evn": 1,
      "mule1": 1,
      "atm": 2
    },
    "timeMin": "2026-09-08T01:15:00+00:00",
    "timeMax": "2026-09-08T02:55:00+00:00",
    "unknownTimeEdgeCount": 0
  },
  "snapshotHash": "815149084195c735e29214354037e530abc7c31b12e8b22ee01c8637babdee03"
};

const mockWorkbenchData = {
  success: true,
  data: {
    case: {
      caseId: "canvas_vn_01",
      seedEntity: "hub",
      evidenceIds: [],
      traceEdgeIds: [
        "TXN-2026-8800",
        "TXN-2026-8801",
        "TXN-2026-8802",
        "TXN-2026-8803",
        "TXN-2026-8804",
        "TXN-2026-8805",
        "TXN-2026-8806",
        "TXN-2026-8807",
        "TXN-2026-8808",
        "TXN-2026-8809"
      ],
      createdAt: "2026-09-08T08:00:00+07:00",
      snapshotHash: traces.snapshotHash,
    },
    evidence: [],
    trace: traces.initial,
    hypothesis: {
      hypothesisId: "hyp-canvas_vn_01",
      caseId: "canvas_vn_01",
      status: "AI_UNAVAILABLE",
      summary: "Hypothesis not generated for this snapshot",
      claims: [],
      generatedAt: "2026-09-08T08:00:00Z",
      modelVersion: null,
    },
    pins: [],
    pinningAvailable: true,
    hypothesisSnapshotHash: null,
  },
  error: null,
};

test.describe("Forensic Canvas Acceptance Suite", () => {
  let pinned = false;

  test.beforeEach(async ({ page }) => {
    pinned = false;

    // 1. Intercept Workbench Data
    await page.route("**/cases/**/workbench", async (route) => {
      const currentPins = pinned
        ? [
            {
              edgeId: "TXN-2026-8804",
              evidenceId: "ev:txn:pinned-8804",
              analystId: "analyst_01",
              typologyTag: "SHELL_CORP",
              updatedAt: "2026-09-08T09:15:00Z",
              transaction: {
                edgeId: "TXN-2026-8804",
                source: "hub",
                target: "shell",
                flowAmount: 140000000,
                relationshipType: "NAPAS_247",
                identityConfidence: 0.98,
                currency: "VND",
                timestamp: "2026-09-08T09:12:00+07:00",
              },
            },
          ]
        : [];

      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          ...mockWorkbenchData,
          data: {
            ...mockWorkbenchData.data,
            pins: currentPins,
          },
        }),
      });
    });

    // 2. Intercept Graph Expansion
    await page.route("**/cases/**/graph/expand", async (route) => {
      const req = route.request();
      const body = JSON.parse(req.postData() || "{}");
      const nodeId = body.nodeId;

      let traceResult = traces.initial;
      if (nodeId === "shell") {
        traceResult = traces.expandShell;
      } else if (nodeId === "atm") {
        traceResult = traces.expandAtm;
      }

      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: traceResult,
          error: null,
        }),
      });
    });

    // 3. Intercept Evidence Pinning
    await page.route("**/cases/**/evidence/pin", async (route) => {
      pinned = true;
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: {
            newSnapshotHash: "hash-new-pinned",
            case: {
              ...mockWorkbenchData.data.case,
              snapshotHash: "hash-new-pinned",
            },
            evidence: [],
            pins: [
              {
                edgeId: "TXN-2026-8804",
                evidenceId: "ev:txn:pinned-8804",
                analystId: "analyst_01",
                typologyTag: "SHELL_CORP",
                updatedAt: "2026-09-08T09:15:00Z",
                transaction: {
                  edgeId: "TXN-2026-8804",
                  source: "hub",
                  target: "shell",
                  flowAmount: 140000000,
                  relationshipType: "NAPAS_247",
                  identityConfidence: 0.98,
                  currency: "VND",
                  timestamp: "2026-09-08T09:12:00+07:00",
                },
              },
            ],
          },
          error: null,
        }),
      });
    });

    // 5. Intercept Hypothesis
    await page.route("**/cases/**/hypothesis", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: {
            snapshotHash: "hash-hypo",
            hypothesis: {
              hypothesisId: "hypo-01",
              caseId: "canvas_vn_01",
              status: "AI_UNAVAILABLE",
              summary: "AI provider disabled in test mode",
              claims: [],
              generatedAt: "2026-09-08T08:00:00Z",
              modelVersion: null,
            },
          },
          error: null,
        }),
      });
    });

    // 4. Intercept Feedback
    await page.route("**/cases/**/feedback", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: { status: "accepted", eventId: "fb-canvas-01" },
          error: null,
        }),
      });
    });
  });

  test("exercises complete analyst journey on canvas_vn_01", async ({ page }) => {
    // Navigate to the root app
    await page.goto("/");

    // Load case canvas_vn_01
    const caseInput = page.locator("input[aria-label='Case ID']");
    await caseInput.fill("canvas_vn_01");
    await page.locator("button:has-text('Load Case')").click();

    // Verify workspace loaded
    await expect(page.locator("text=Vụ án: canvas_vn_01")).toBeVisible({ timeout: 15000 });
    await expect(page.locator("[data-testid='seed-entity']")).toContainText("hub");

    // 1. Initial 1-hop boundary verification
    await expect(page.locator("[data-node-id='hub']")).toBeVisible();
    await expect(page.locator("[data-node-id='shell']")).toBeVisible();
    await expect(page.locator("[data-node-id='mule1']")).toBeVisible();
    await expect(page.locator("[data-node-id='atm']")).not.toBeVisible();
    await expect(page.locator("[data-node-id='crypto']")).not.toBeVisible();
    await expect(page.locator("[data-node-id='exit3']")).not.toBeVisible();
    await expect(page.locator("[data-node-id='exit4']")).not.toBeVisible();

    // 2. Hop expansion
    // Select shell and expand
    await page.locator("[data-node-id='shell']").click({ force: true });
    await page.waitForTimeout(300);
    const expandBtn = page.locator("button:has-text('Mở rộng Hop')");
    await expect(expandBtn).toBeEnabled();
    await expandBtn.click();

    // atm and crypto should become visible (hop 2)
    await expect(page.locator("[data-node-id='atm']")).toBeVisible({ timeout: 10000 });
    await expect(page.locator("[data-node-id='crypto']")).toBeVisible();

    // Select atm and expand
    await page.locator("[data-node-id='atm']").click({ force: true });
    await page.waitForTimeout(300);
    await expect(expandBtn).toBeEnabled();
    await expandBtn.click();

    // exit3 becomes visible (hop 3)
    await expect(page.locator("[data-node-id='exit3']")).toBeVisible({ timeout: 10000 });
    // exit4 (hop 4) must NEVER be visible
    await expect(page.locator("[data-node-id='exit4']")).not.toBeVisible();

    // 3. Layout switching
    await page.locator("button:has-text('CoSE (2)')").click();
    await page.locator("button:has-text('Concentric (3)')").click();
    await page.locator("button:has-text('Causal (1)')").click();

    // 4. Keyboard safety while typing in Analyst ID
    const analystInput = page.locator("input[placeholder*='analyst_01']");
    await analystInput.click();
    await analystInput.fill("analyst_01 f 1 2 3 p");
    // Verify typed letters didn't trigger layout or playback
    expect(await analystInput.inputValue()).toBe("analyst_01 f 1 2 3 p");

    // Clean to valid analyst ID
    await analystInput.fill("analyst_01");

    // 5. Pin transaction to SAR
    // Select transaction TXN-2026-8804
    const edgeLabel = page.locator("[data-edge-id='TXN-2026-8804']");
    if (await edgeLabel.isVisible()) {
      await edgeLabel.click();
    } else {
      // Click through details list if edge label is displaced
      await page.locator("text=TXN-2026-8804").first().click();
    }

    const pinBtn = page.locator("button[data-testid='pin-toggle-btn']");
    await expect(pinBtn).toBeEnabled();
    await pinBtn.click();

    // Verify pinned in dossier
    await expect(page.locator("text=Chứng cứ đã ghim (1)")).toBeVisible({ timeout: 10000 });
    await expect(page.locator("span:has-text('GHIM SAR')").first()).toBeVisible();

    // 6. Submit feedback
    const select = page.getByLabel("Kết luận xử lý (Disposition):");
    await select.selectOption("ESCALATE");

    const reasonText = page.getByLabel("Lý do đánh giá (Rationale) *:");
    await reasonText.fill("Phát hiện chuỗi giao dịch smurfing và công ty bình phong Nam Phát.");

    const submitFeedbackBtn = page.locator("button:has-text('Gửi đánh giá vụ án')");
    await expect(submitFeedbackBtn).toBeEnabled();
    await submitFeedbackBtn.click();

    await expect(page.locator("text=Đã lưu phản hồi thành công!")).toBeVisible({ timeout: 10000 });
  });
});
