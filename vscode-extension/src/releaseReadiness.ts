/**
 * One release-readiness checklist item.
 */
export interface ReleaseChecklistItem {
  label: string;
  detail: string;
}

/**
 * One section in the public-release checklist.
 */
export interface ReleaseChecklistSection {
  title: string;
  items: ReleaseChecklistItem[];
}

/**
 * Returns the release-readiness sections used by both tests and Markdown
 * rendering. Keeping this as data makes the release gate easy to review.
 */
export function releaseChecklistSections(): ReleaseChecklistSection[] {
  return [
    {
      title: "Local quality gates",
      items: [
        {
          label: "Python tests pass",
          detail: "`python3 -m unittest discover -s tests -q` passes from the repo root."
        },
        {
          label: "VS Code extension tests pass",
          detail: "`npm test` passes from `vscode-extension/`."
        },
        {
          label: "Vague prompt benchmark passes",
          detail: "`python3 scripts/benchmark_vague_prompts.py --min-block-rate 0.90` passes."
        },
        {
          label: "Template docs are current",
          detail: "`python3 scripts/generate_template_docs.py --check` passes."
        }
      ]
    },
    {
      title: "VS Code clean-install gates",
      items: [
        {
          label: "Clean VSIX install works",
          detail: "Install the generated VSIX into a clean VS Code profile or a machine without the dev extension."
        },
        {
          label: "Setup Doctor is green",
          detail: "`Prompt Preflight: Run Setup Doctor` shows no duplicate-extension or missing-analyzer failures."
        },
        {
          label: "Core prompt check works",
          detail: "A Markdown prompt with `Create a car image` opens a result tab with image-specific questions."
        },
        {
          label: "Telemetry dashboard works",
          detail: "After telemetry is enabled and one check runs, `Prompt Preflight: Open Telemetry Dashboard` shows local graph data."
        },
        {
          label: "Generated-tab cleanup works",
          detail: "`Prompt Preflight: Close Generated Tabs` closes result/template/composer tabs without closing normal files."
        }
      ]
    },
    {
      title: "Public packaging gates",
      items: [
        {
          label: "Bundled analyzer is packaged",
          detail: "The Marketplace VSIX includes `bundled-analyzer/scripts/prompt_preflight.py`; `promptPreflight.repoPath` is only a developer override."
        },
        {
          label: "Publisher account and token are ready",
          detail: "VS Code Marketplace publisher setup is complete and the publishing token is stored outside the repo."
        },
        {
          label: "Versioning is decided",
          detail: "Choose release version, changelog format, and whether this is public beta or stable."
        },
        {
          label: "Package contents are audited",
          detail: "`npm run package:list` and `npm run package:audit` include only intended extension files plus the bundled analyzer, and exclude raw videos, node_modules, telemetry, local config, source, tests, and release tooling."
        }
      ]
    },
    {
      title: "Docs and launch gates",
      items: [
        {
          label: "README has current demo assets",
          detail: "Root README includes the GIF/image assets and describes Codex, Claude, Kiro, CLI, and VS Code support accurately."
        },
        {
          label: "VS Code README has screenshots or GIFs",
          detail: "Extension README shows prompt check, suggested prompt insertion, Setup Doctor, and telemetry dashboard."
        },
        {
          label: "Install docs are external-user friendly",
          detail: "Docs explain VSIX install, Python 3.10+, optional repoPath developer override, and common troubleshooting."
        },
        {
          label: "Launch copy is aligned",
          detail: "`docs/LAUNCH.md` and README claims match the latest benchmark and feature status."
        }
      ]
    },
    {
      title: "Privacy and safety gates",
      items: [
        {
          label: "Telemetry remains local and prompt-free",
          detail: "Telemetry does not store prompt text, response text, suggested rewrites, questions, reason strings, or file contents."
        },
        {
          label: "Secret detection blocks and redacts",
          detail: "A likely pasted credential blocks before model work and user-facing output redacts the secret."
        },
        {
          label: "Hooks fail open safely",
          detail: "Codex, Claude, Kiro, and postflight hook adapters do not make the host unusable on malformed payloads."
        },
        {
          label: "No owner-specific website config is accidentally published",
          detail: "AdSense snippets or other owner-only deployment settings are not committed unless intentionally building the website."
        }
      ]
    },
    {
      title: "Repo hygiene gates",
      items: [
        {
          label: "Worktree is reviewed",
          detail: "Remove, ignore, or intentionally commit scratch files, local test prompts, generated VSIX files, and repair scripts."
        },
        {
          label: "GitHub metadata is ready",
          detail: "Repo description, topics, social preview, good-first-issue labels, and contribution notes are polished."
        },
        {
          label: "Issues are curated",
          detail: "Open follow-up issues for known improvements without duplicating existing issues."
        }
      ]
    }
  ];
}

/**
 * Renders the release-readiness checklist as Markdown for VS Code users.
 */
export function releaseReadinessMarkdown(): string {
  const lines = [
    "# Prompt Preflight Release Readiness Checklist",
    "",
    "Use this checklist before publishing the VS Code extension or announcing the repo broadly.",
    "",
    "Public release is ready only when every blocking item below is checked or explicitly deferred.",
    ""
  ];

  for (const section of releaseChecklistSections()) {
    lines.push(`## ${section.title}`, "");
    for (const item of section.items) {
      lines.push(`- [ ] **${item.label}** — ${item.detail}`);
    }
    lines.push("");
  }

  lines.push(
    "## Release call",
    "",
    "- [ ] We are comfortable calling this a public beta.",
    "- [ ] Known limitations are documented instead of hidden.",
    "- [ ] A clean user can install, run a check, view Setup Doctor, and view telemetry without help.",
    "",
    "When those are true, it is time to release publicly."
  );

  return lines.join("\n");
}
