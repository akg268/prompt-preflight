import * as vscode from "vscode";
import {
  COMPOSER_PROFILE_SPECS,
  DEFAULT_COMPOSER_FORM,
  buildComposedPrompt
} from "./composerPrompt";
import { trackGeneratedPromptDocument } from "./generatedTabs";

/**
 * Callback used by the composer to run Prompt Preflight against generated text.
 */
export type PromptCheckCallback = (prompt: string) => Promise<void>;

/**
 * Manages the Prompt Composer webview panel.
 */
export class PromptComposerPanel {
  private static currentPanel: PromptComposerPanel | undefined;

  /**
   * Opens a singleton Prompt Composer panel.
   */
  static open(context: vscode.ExtensionContext, checkPrompt: PromptCheckCallback): void {
    if (PromptComposerPanel.currentPanel) {
      PromptComposerPanel.currentPanel.panel.reveal(vscode.ViewColumn.Beside);
      return;
    }

    const panel = vscode.window.createWebviewPanel(
      "promptPreflightComposer",
      "Prompt Preflight Composer",
      vscode.ViewColumn.Beside,
      {
        enableScripts: true,
        retainContextWhenHidden: true
      }
    );

    PromptComposerPanel.currentPanel = new PromptComposerPanel(panel, context, checkPrompt);
  }

  /**
   * Wires the webview HTML and message handlers.
   */
  private constructor(
    private readonly panel: vscode.WebviewPanel,
    private readonly context: vscode.ExtensionContext,
    private readonly checkPrompt: PromptCheckCallback
  ) {
    this.panel.webview.html = composerHtml(this.panel.webview);
    this.panel.onDidDispose(() => {
      PromptComposerPanel.currentPanel = undefined;
    });
    this.panel.webview.onDidReceiveMessage((message) => {
      void this.handleMessage(message);
    });
  }

  /**
   * Handles messages from the Prompt Composer webview.
   */
  private async handleMessage(message: { type?: string; prompt?: string }): Promise<void> {
    const prompt = message.prompt?.trim();
    if (!prompt) {
      void vscode.window.showWarningMessage("Prompt Preflight: fill in the composer fields first.");
      return;
    }

    if (message.type === "createMarkdown") {
      await openPromptDocument(prompt);
      return;
    }

    if (message.type === "copyPrompt") {
      await vscode.env.clipboard.writeText(prompt);
      void vscode.window.showInformationMessage("Prompt Preflight: composed prompt copied.");
      return;
    }

    if (message.type === "checkPrompt") {
      await this.checkPrompt(prompt);
    }
  }
}

/**
 * Opens a new Markdown document populated with the composed prompt.
 */
async function openPromptDocument(prompt: string): Promise<void> {
  const document = await vscode.workspace.openTextDocument({
    language: "markdown",
    content: prompt
  });
  trackGeneratedPromptDocument(document, "composer");
  await vscode.window.showTextDocument(document, vscode.ViewColumn.Beside);
}

/**
 * Builds the full Prompt Composer webview HTML.
 */
function composerHtml(webview: vscode.Webview): string {
  const nonce = nonceValue();
  const initialPrompt = jsonForScript(buildComposedPrompt(DEFAULT_COMPOSER_FORM));
  const profileOptions = COMPOSER_PROFILE_SPECS.map(
    (spec) => `<option value="${escapeHtml(spec.value)}">${escapeHtml(spec.label)}</option>`
  ).join("\n        ");
  const profileSpecs = jsonForScript(COMPOSER_PROFILE_SPECS);
  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta
    http-equiv="Content-Security-Policy"
    content="default-src 'none'; style-src ${webview.cspSource} 'unsafe-inline'; script-src 'nonce-${nonce}';"
  >
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Prompt Preflight Composer</title>
  <style>
    body { font-family: var(--vscode-font-family); color: var(--vscode-foreground); background: var(--vscode-editor-background); padding: 16px; }
    .layout { display: grid; grid-template-columns: minmax(280px, 1fr) minmax(280px, 1fr); gap: 16px; }
    label { display: block; margin: 12px 0 4px; font-weight: 600; }
    select, textarea, input { width: 100%; box-sizing: border-box; color: var(--vscode-input-foreground); background: var(--vscode-input-background); border: 1px solid var(--vscode-input-border); padding: 8px; }
    textarea { min-height: 72px; resize: vertical; }
    .actions { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 12px; }
    button { color: var(--vscode-button-foreground); background: var(--vscode-button-background); border: none; padding: 8px 12px; cursor: pointer; }
    button.secondary { color: var(--vscode-button-secondaryForeground); background: var(--vscode-button-secondaryBackground); }
    pre { white-space: pre-wrap; border: 1px solid var(--vscode-editorWidget-border); padding: 12px; min-height: 480px; overflow: auto; }
    .hint { color: var(--vscode-descriptionForeground); }
    .required-note { color: var(--vscode-testing-iconFailed); font-weight: 500; }
  </style>
</head>
<body>
  <h1>Prompt Preflight Composer</h1>
  <p class="hint">Fill the required fields, preview the prompt, then create a Markdown file or run Prompt Preflight.</p>
  <div class="layout">
    <section>
      <label for="profile">Profile</label>
      <select id="profile">
        ${profileOptions}
      </select>

      <label for="task">Task</label>
      <textarea id="task" placeholder="What should the AI agent do?"></textarea>

      <label for="context">Context</label>
      <textarea id="context" placeholder="Relevant background, files, source material, or links"></textarea>

      <label for="outputFormat">Output format</label>
      <textarea id="outputFormat" placeholder="Exact structure: bullets, table, JSON, patch, image specs, etc."></textarea>

      <label for="successCriteria">Success criteria</label>
      <textarea id="successCriteria" placeholder="One criterion per line"></textarea>

      <label id="constraintsLabel" for="constraints">Optional constraints</label>
      <textarea id="constraints" placeholder="Boundaries or things to preserve"></textarea>

      <label for="examples">Optional examples</label>
      <textarea id="examples" placeholder="Sample output, style reference, or example to imitate"></textarea>

      <div class="actions">
        <button id="createMarkdown">Create Markdown file</button>
        <button id="checkPrompt">Run Prompt Preflight</button>
        <button id="copyPrompt" class="secondary">Copy prompt</button>
      </div>
    </section>
    <section>
      <h2>Preview</h2>
      <pre id="preview">${escapeHtml(JSON.parse(initialPrompt))}</pre>
    </section>
  </div>
  <script nonce="${nonce}">
    const vscode = acquireVsCodeApi();
    const profileSpecs = ${profileSpecs};
    const fields = ["profile", "task", "context", "outputFormat", "successCriteria", "constraints", "examples"];
    const preview = document.getElementById("preview");
    const constraintsLabel = document.getElementById("constraintsLabel");
    const constraintsField = document.getElementById("constraints");

    function cleanInline(value) {
      return (value || "").replace(/-->/g, "").trim() || "general";
    }

    function profileSpec(profile) {
      return profileSpecs.find((spec) => spec.value === cleanInline(profile)) || profileSpecs[0];
    }

    function constraintsRequired(profile) {
      return profileSpec(profile).constraintsRequired;
    }

    function fieldOrPlaceholder(value, placeholder) {
      return (value || "").trim() || placeholder;
    }

    function bulletLinesOrPlaceholder(value, placeholder) {
      const lines = (value || "").split(/\\r?\\n/).map((line) => line.trim()).filter(Boolean);
      return lines.length ? lines.map((line) => line.startsWith("-") ? line : "- " + line).join("\\n") : placeholder;
    }

    function inlineValue(value) {
      return (value || "").trim().replace(/\\s+/g, " ");
    }

    function formData() {
      const data = {};
      for (const field of fields) {
        data[field] = document.getElementById(field).value;
      }
      return data;
    }

    function buildPrompt(data) {
      const sections = [
        "<!-- prompt-preflight: check -->",
        "",
        "<!-- profile: " + cleanInline(data.profile) + " -->",
        "",
        "# Task",
        fieldOrPlaceholder(data.task, "[What should the AI agent do?]"),
        "",
        "# Context",
        fieldOrPlaceholder(data.context, "[Relevant background, files, source material, or links]")
      ];

      if (constraintsRequired(data.profile)) {
        sections.push(
          "",
          "# Constraints",
          bulletLinesOrPlaceholder(
            data.constraints,
            "- [Required boundaries, things to preserve, and out-of-scope areas]"
          )
        );
      }

      sections.push(
        "",
        "# Output Format",
        fieldOrPlaceholder(data.outputFormat, "[Exact structure: bullets, table, JSON, patch, image specs, etc.]"),
        "",
        "# Success Criteria",
        bulletLinesOrPlaceholder(data.successCriteria, "- [How should the result be verified?]")
      );

      const optionalLines = [];
      if (!constraintsRequired(data.profile) && (data.constraints || "").trim()) {
        optionalLines.push("- Constraints: " + inlineValue(data.constraints));
      }
      if ((data.examples || "").trim()) {
        optionalLines.push("- Examples: " + inlineValue(data.examples));
      }
      if (optionalLines.length) {
        sections.push("", "# Optional", ...optionalLines);
      }

      return sections.join("\\n").trimEnd() + "\\n";
    }

    function refreshProfileUi() {
      if (constraintsRequired(document.getElementById("profile").value)) {
        constraintsLabel.innerHTML = 'Constraints <span class="required-note">(required for this profile)</span>';
        constraintsField.placeholder = "Required boundaries, things to preserve, and out-of-scope areas";
        constraintsField.setAttribute("aria-required", "true");
      } else {
        constraintsLabel.textContent = "Optional constraints";
        constraintsField.placeholder = "Boundaries or things to preserve";
        constraintsField.setAttribute("aria-required", "false");
      }
    }

    function refreshPreview() {
      refreshProfileUi();
      preview.textContent = buildPrompt(formData());
    }

    for (const field of fields) {
      document.getElementById(field).addEventListener("input", refreshPreview);
      document.getElementById(field).addEventListener("change", refreshPreview);
    }

    for (const action of ["createMarkdown", "checkPrompt", "copyPrompt"]) {
      document.getElementById(action).addEventListener("click", () => {
        vscode.postMessage({ type: action, prompt: buildPrompt(formData()) });
      });
    }

    refreshPreview();
  </script>
</body>
</html>`;
}

/**
 * Escapes HTML special characters for safe rendering in a preview element.
 */
function escapeHtml(value: string): string {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

/**
 * Generates a nonce for the webview content security policy.
 */
function nonceValue(): string {
  const alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789";
  let nonce = "";
  for (let index = 0; index < 32; index += 1) {
    nonce += alphabet.charAt(Math.floor(Math.random() * alphabet.length));
  }
  return nonce;
}

/**
 * Serializes a value for safe insertion inside a script-free HTML expression.
 */
function jsonForScript(value: unknown): string {
  return JSON.stringify(value).replace(/</g, "\\u003c");
}
