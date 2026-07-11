import { runComposerPromptTests } from "./composerPrompt.test";
import { runDiagnosticRulesTests } from "./diagnosticRules.test";
import { runGeneratedDocumentsTests } from "./generatedDocuments.test";
import { runPolicyDocumentTests } from "./policyDocument.test";
import { runRepoResolverTests } from "./repoResolver.test";
import { runReleaseReadinessTests } from "./releaseReadiness.test";
import { runSetupDoctorTests } from "./setupDoctor.test";
import { runTelemetryStoreTests } from "./telemetryStore.test";
import { runTemplateDocumentTests } from "./templateDocument.test";
import { runWorkspaceLintRulesTests } from "./workspaceLintRules.test";

/**
 * Runs all dependency-free extension unit tests.
 */
function main(): void {
  runComposerPromptTests();
  runDiagnosticRulesTests();
  runGeneratedDocumentsTests();
  runTemplateDocumentTests();
  runWorkspaceLintRulesTests();
  runPolicyDocumentTests();
  runRepoResolverTests();
  runReleaseReadinessTests();
  runSetupDoctorTests();
  runTelemetryStoreTests();

  if (process.exitCode) {
    return;
  }
  console.log("\nAll extension unit tests passed.");
}

main();
