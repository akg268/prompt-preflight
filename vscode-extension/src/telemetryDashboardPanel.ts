import * as vscode from "vscode";
import {
  loadTelemetryDashboardSummary,
  TelemetryBar,
  TelemetryDashboardSummary
} from "./telemetryStore";

/**
 * Owns the Prompt Preflight telemetry dashboard webview.
 */
export class TelemetryDashboardPanel {
  private static currentPanel: TelemetryDashboardPanel | undefined;

  private readonly panel: vscode.WebviewPanel;
  private readonly extensionUri: vscode.Uri;
  private readonly workspacePath: string;
  private readonly disposables: vscode.Disposable[] = [];

  /**
   * Opens or reveals the singleton dashboard panel for the active workspace.
   */
  static open(context: vscode.ExtensionContext, workspacePath?: string): void {
    if (!workspacePath) {
      void vscode.window.showWarningMessage(
        "Prompt Preflight: open a workspace folder before viewing telemetry."
      );
      return;
    }

    if (TelemetryDashboardPanel.currentPanel?.workspacePath === workspacePath) {
      TelemetryDashboardPanel.currentPanel.panel.reveal(vscode.ViewColumn.Beside);
      TelemetryDashboardPanel.currentPanel.refresh();
      return;
    }
    TelemetryDashboardPanel.currentPanel?.panel.dispose();

    const panel = vscode.window.createWebviewPanel(
      "promptPreflightTelemetry",
      "Prompt Preflight Telemetry",
      vscode.ViewColumn.Beside,
      {
        enableScripts: true,
        retainContextWhenHidden: true
      }
    );

    TelemetryDashboardPanel.currentPanel = new TelemetryDashboardPanel(
      panel,
      context.extensionUri,
      workspacePath
    );
  }

  /**
   * Creates a dashboard controller and wires webview lifecycle callbacks.
   */
  private constructor(panel: vscode.WebviewPanel, extensionUri: vscode.Uri, workspacePath: string) {
    this.panel = panel;
    this.extensionUri = extensionUri;
    this.workspacePath = workspacePath;

    this.refresh();

    this.panel.onDidDispose(() => this.dispose(), null, this.disposables);
    this.panel.webview.onDidReceiveMessage(
      (message: { type?: string }) => {
        if (message.type === "refresh") {
          this.refresh();
        }
        if (message.type === "enableTelemetry") {
          void vscode.commands.executeCommand("promptPreflight.enableTelemetry");
        }
      },
      null,
      this.disposables
    );
  }

  /**
   * Re-reads local telemetry and updates the dashboard HTML.
   */
  private refresh(): void {
    try {
      const summary = loadTelemetryDashboardSummary(this.workspacePath);
      this.panel.webview.html = dashboardHtml(this.panel.webview, this.extensionUri, summary);
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      this.panel.webview.html = errorHtml(this.panel.webview, this.extensionUri, message);
    }
  }

  /**
   * Releases webview subscriptions when VS Code closes the dashboard tab.
   */
  private dispose(): void {
    TelemetryDashboardPanel.currentPanel = undefined;
    while (this.disposables.length) {
      const disposable = this.disposables.pop();
      disposable?.dispose();
    }
  }
}

/**
 * Builds the full telemetry dashboard document.
 */
function dashboardHtml(
  webview: vscode.Webview,
  extensionUri: vscode.Uri,
  summary: TelemetryDashboardSummary
): string {
  const nonce = nonceValue();
  const cspSource = webview.cspSource;
  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta
    http-equiv="Content-Security-Policy"
    content="default-src 'none'; img-src ${cspSource}; style-src ${cspSource} 'unsafe-inline'; script-src 'nonce-${nonce}';"
  >
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Prompt Preflight Telemetry</title>
  ${dashboardStyles()}
</head>
<body>
  <main>
    <header class="hero">
      <div>
        <p class="eyebrow">Local telemetry dashboard</p>
        <h1>Prompt Preflight</h1>
        <p class="subtle">Prompt-free counts and token estimates stored on this machine.</p>
      </div>
      <button id="refresh" type="button">Refresh</button>
    </header>

    ${statusBanner(summary)}
    ${summaryCards(summary)}

    <section class="grid two">
      ${barChart("Preflight decisions", summary.decisions, "No preflight events yet.")}
      ${barChart("Checks causing blocks", summary.blockedByCheck, "No blocked checks yet.")}
    </section>

    <section class="grid two">
      ${barChart("Daily activity", summary.dailyEvents, "No dated events yet.")}
      ${barChart("Hosts", summary.hosts, "No host data yet.")}
    </section>

    <section class="grid two">
      ${barChart("Prompt token risk", summary.tokens.promptRisk, "No prompt token estimates yet.")}
      ${barChart("Response token risk", summary.tokens.responseRisk, "No response token estimates yet.")}
    </section>

    <section class="grid two">
      ${barChart(
        "Postflight checks causing blocks",
        summary.postflightBlockedByCheck,
        "No postflight blocks yet."
      )}
      ${privacyPanel()}
    </section>
  </main>

  <script nonce="${nonce}">
    const vscode = acquireVsCodeApi();
    document.getElementById("refresh").addEventListener("click", () => {
      vscode.postMessage({ type: "refresh" });
    });
    const openPolicy = document.getElementById("openPolicy");
    if (openPolicy) {
      openPolicy.addEventListener("click", () => {
        vscode.postMessage({ type: "enableTelemetry" });
      });
    }
  </script>
</body>
</html>`;
}

/**
 * Builds the fallback HTML shown when telemetry cannot be read.
 */
function errorHtml(webview: vscode.Webview, extensionUri: vscode.Uri, message: string): string {
  const nonce = nonceValue();
  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta
    http-equiv="Content-Security-Policy"
    content="default-src 'none'; style-src ${webview.cspSource} 'unsafe-inline'; script-src 'nonce-${nonce}';"
  >
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Prompt Preflight Telemetry</title>
  ${dashboardStyles()}
</head>
<body>
  <main>
    <section class="panel">
      <p class="eyebrow">Telemetry dashboard</p>
      <h1>Could not load telemetry</h1>
      <p>${escapeHtml(message)}</p>
    </section>
  </main>
</body>
</html>`;
}

/**
 * Renders a telemetry status banner with file path and opt-in state.
 */
function statusBanner(summary: TelemetryDashboardSummary): string {
  const enabledClass = summary.telemetryEnabled ? "good" : "warn";
  const enabledText = summary.telemetryEnabled ? "Telemetry recording enabled" : "Telemetry recording disabled";
  const helper = summary.telemetryEnabled
    ? "VS Code checks will append prompt-free events because .prompt-preflight.json enables telemetry."
    : summary.policySource === "default"
      ? "No .prompt-preflight.json policy was found. Create one and set telemetry.enabled to true to record new VS Code checks."
      : "The policy file exists, but new VS Code checks will not be recorded until telemetry.enabled is true. Top-level enabled only controls Prompt Preflight checks.";
  const malformed = summary.malformedLines
    ? `<p class="warning">${summary.malformedLines} malformed telemetry line${plural(summary.malformedLines)} skipped.</p>`
    : "";
  const policyAction = summary.telemetryEnabled
    ? ""
    : `<button id="openPolicy" class="secondary" type="button">Enable local telemetry</button>`;

  return `<section class="status panel">
    <div>
      <span class="pill ${enabledClass}">${enabledText}</span>
      <p>${escapeHtml(helper)}</p>
      ${malformed}
      ${policyAction}
    </div>
    <div class="path">
      <span>Local file</span>
      <code>${escapeHtml(summary.telemetryPath)}</code>
    </div>
  </section>`;
}

/**
 * Renders the top KPI cards.
 */
function summaryCards(summary: TelemetryDashboardSummary): string {
  const cards = [
    metricCard("Events read", summary.eventsRead, "all local telemetry events"),
    metricCard("Prompts checked", summary.promptsChecked, "preflight events"),
    metricCard("Blocked before model", summary.promptsBlocked, "likely avoided bad turns"),
    metricCard("Postflight flags", summary.postflightResponsesBlocked, "responses needing attention"),
    metricCard(
      "Request tokens reserved",
      summary.tokens.estimatedRequestTokensTotal,
      "estimated prompt + max output"
    ),
    metricCard(
      "Avoided retry token opportunity",
      summary.tokens.estimatedAvoidedRetryTokens,
      "estimated from blocked prompts"
    )
  ];
  return `<section class="cards">${cards.join("")}</section>`;
}

/**
 * Renders one numeric dashboard card.
 */
function metricCard(label: string, value: number, hint: string): string {
  return `<article class="card">
    <span>${escapeHtml(label)}</span>
    <strong>${formatNumber(value)}</strong>
    <small>${escapeHtml(hint)}</small>
  </article>`;
}

/**
 * Renders one horizontal bar chart from count bars.
 */
function barChart(title: string, bars: TelemetryBar[], emptyText: string): string {
  const max = bars.reduce((largest, bar) => Math.max(largest, bar.value), 0);
  const rows = bars.length
    ? bars
        .map((bar) => {
          const width = max > 0 ? Math.max(4, Math.round((bar.value / max) * 100)) : 0;
          return `<div class="bar-row">
            <div class="bar-label">${escapeHtml(bar.label)}</div>
            <div class="bar-track"><div class="bar-fill" style="width:${width}%"></div></div>
            <div class="bar-value">${formatNumber(bar.value)}</div>
          </div>`;
        })
        .join("")
    : `<p class="empty">${escapeHtml(emptyText)}</p>`;

  return `<article class="panel chart">
    <h2>${escapeHtml(title)}</h2>
    ${rows}
  </article>`;
}

/**
 * Renders the privacy explanation panel.
 */
function privacyPanel(): string {
  return `<article class="panel">
    <h2>Privacy guardrails</h2>
    <ul>
      <li>Telemetry is stored locally on this machine.</li>
      <li>The dashboard reads numeric counts, decisions, hosts, checks, and token estimates.</li>
      <li>Prompt text, response text, suggested rewrites, questions, and reason strings are not stored.</li>
      <li>Token numbers are local estimates, not provider billing records.</li>
    </ul>
  </article>`;
}

/**
 * Returns the dashboard CSS.
 */
function dashboardStyles(): string {
  return `<style>
    :root {
      color-scheme: light dark;
      --bg: var(--vscode-editor-background);
      --fg: var(--vscode-editor-foreground);
      --muted: var(--vscode-descriptionForeground);
      --panel: color-mix(in srgb, var(--vscode-editor-background) 86%, var(--vscode-editor-foreground) 14%);
      --border: color-mix(in srgb, var(--vscode-editor-background) 65%, var(--vscode-editor-foreground) 35%);
      --accent: #4aa3ff;
      --accent-2: #68d391;
      --warn: #f6ad55;
    }
    body {
      margin: 0;
      background: radial-gradient(circle at top left, rgba(74, 163, 255, 0.16), transparent 34rem), var(--bg);
      color: var(--fg);
      font-family: var(--vscode-font-family);
    }
    main {
      max-width: 1180px;
      margin: 0 auto;
      padding: 28px;
    }
    .hero {
      display: flex;
      justify-content: space-between;
      gap: 20px;
      align-items: center;
      margin-bottom: 18px;
    }
    h1, h2, p {
      margin-top: 0;
    }
    h1 {
      font-size: 34px;
      margin-bottom: 8px;
    }
    h2 {
      font-size: 17px;
      margin-bottom: 16px;
    }
    button {
      border: 0;
      border-radius: 999px;
      padding: 10px 16px;
      color: #04111f;
      background: linear-gradient(135deg, var(--accent), var(--accent-2));
      font-weight: 700;
      cursor: pointer;
    }
    button.secondary {
      margin-top: 8px;
      color: var(--fg);
      background: rgba(127, 127, 127, 0.18);
      border: 1px solid var(--border);
    }
    .eyebrow {
      color: var(--accent);
      text-transform: uppercase;
      letter-spacing: 0.08em;
      font-size: 12px;
      font-weight: 700;
      margin-bottom: 8px;
    }
    .subtle, .empty, small {
      color: var(--muted);
    }
    .panel, .card {
      border: 1px solid var(--border);
      border-radius: 18px;
      background: color-mix(in srgb, var(--panel) 82%, transparent);
      box-shadow: 0 18px 38px rgba(0, 0, 0, 0.14);
    }
    .status {
      display: grid;
      grid-template-columns: minmax(0, 1fr) minmax(240px, 420px);
      gap: 18px;
      padding: 18px;
      margin-bottom: 18px;
    }
    .pill {
      display: inline-block;
      border-radius: 999px;
      padding: 6px 10px;
      font-size: 12px;
      font-weight: 700;
      margin-bottom: 10px;
    }
    .pill.good {
      background: rgba(104, 211, 145, 0.16);
      color: var(--accent-2);
    }
    .pill.warn {
      background: rgba(246, 173, 85, 0.16);
      color: var(--warn);
    }
    .warning {
      color: var(--warn);
      margin-bottom: 0;
    }
    .path span {
      display: block;
      color: var(--muted);
      font-size: 12px;
      margin-bottom: 6px;
    }
    code {
      display: block;
      white-space: pre-wrap;
      word-break: break-word;
      font-size: 12px;
      color: var(--fg);
    }
    .cards {
      display: grid;
      grid-template-columns: repeat(6, minmax(0, 1fr));
      gap: 12px;
      margin-bottom: 18px;
    }
    .card {
      padding: 16px;
      min-height: 112px;
    }
    .card span, .card small {
      display: block;
    }
    .card strong {
      display: block;
      font-size: 28px;
      margin: 10px 0 8px;
    }
    .grid {
      display: grid;
      gap: 18px;
      margin-bottom: 18px;
    }
    .grid.two {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }
    .chart, .panel {
      padding: 18px;
    }
    .bar-row {
      display: grid;
      grid-template-columns: 148px minmax(100px, 1fr) 58px;
      align-items: center;
      gap: 10px;
      margin: 10px 0;
    }
    .bar-label {
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      color: var(--muted);
    }
    .bar-track {
      height: 13px;
      overflow: hidden;
      border-radius: 999px;
      background: rgba(127, 127, 127, 0.18);
    }
    .bar-fill {
      height: 100%;
      border-radius: inherit;
      background: linear-gradient(90deg, var(--accent), var(--accent-2));
    }
    .bar-value {
      text-align: right;
      font-variant-numeric: tabular-nums;
    }
    li {
      margin: 8px 0;
    }
    @media (max-width: 980px) {
      .cards {
        grid-template-columns: repeat(2, minmax(0, 1fr));
      }
      .grid.two, .status {
        grid-template-columns: 1fr;
      }
    }
  </style>`;
}

/**
 * Escapes user-controlled text for safe HTML rendering.
 */
function escapeHtml(value: string): string {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

/**
 * Formats dashboard numbers with local thousands separators.
 */
function formatNumber(value: number): string {
  return Math.round(value).toLocaleString();
}

/**
 * Returns the plural suffix for a count.
 */
function plural(value: number): string {
  return value === 1 ? "" : "s";
}

/**
 * Generates a CSP nonce for the refresh script.
 */
function nonceValue(): string {
  const chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789";
  let text = "";
  for (let index = 0; index < 32; index += 1) {
    text += chars.charAt(Math.floor(Math.random() * chars.length));
  }
  return text;
}
