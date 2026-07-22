import assert from "assert/strict";
import * as fs from "fs";
import * as path from "path";
import {
  openSpecTemplate,
  SPEC_TEMPLATE_COMMANDS,
  SpecTemplateCatalog
} from "../specTemplateCommands";
import {
  FORMAT_LANGUAGE,
  TemplateDocumentSpec,
  TemplateFormat,
  TEMPLATE_FORMAT_ORDER
} from "../templateDocument";
import { AsyncTestCase, runAsyncSuite } from "./testHarness";

/**
 * Loads the same shared catalog used by the extension at runtime.
 */
function loadCatalog(): SpecTemplateCatalog {
  const catalogPath = path.resolve(
    __dirname,
    "..",
    "..",
    "..",
    "src",
    "prompt_preflight",
    "data",
    "prompt_templates.json"
  );
  return JSON.parse(fs.readFileSync(catalogPath, "utf-8")) as SpecTemplateCatalog;
}

/**
 * Builds one routing test for a command/profile/format combination.
 */
function routingTest(
  command: string,
  profileKey: (typeof SPEC_TEMPLATE_COMMANDS)[number]["profileKey"],
  format: TemplateFormat,
  catalog: SpecTemplateCatalog
): AsyncTestCase {
  return {
    name: `routes ${command} to its ${format} untitled template`,
    run: async () => {
      const openedDocuments: TemplateDocumentSpec[] = [];

      await openSpecTemplate(profileKey, {
        chooseFormat: async () => format,
        loadCatalog: async () => catalog,
        openUntitledDocument: async (document) => {
          openedDocuments.push(document);
        }
      });

      const expectedLines = catalog.profiles[profileKey].templates[format];
      assert.ok(expectedLines);
      assert.equal(openedDocuments.length, 1);
      assert.deepEqual(openedDocuments[0], {
        language: FORMAT_LANGUAGE[format],
        content: `${expectedLines.join("\n").trimEnd()}\n`
      });
    }
  };
}

/**
 * Unit tests for direct spec-template command routing.
 */
export async function runSpecTemplateCommandTests(): Promise<void> {
  const catalog = loadCatalog();
  const routingTests = SPEC_TEMPLATE_COMMANDS.flatMap(({ command, profileKey }) =>
    TEMPLATE_FORMAT_ORDER.map((format) =>
      routingTest(command, profileKey, format, catalog)
    )
  );

  await runAsyncSuite("specTemplateCommands", [
    ...routingTests,
    {
      name: "opens an untitled document without modifying the active source",
      run: async () => {
        const activeSource = {
          uri: "file:///workspace/source.md",
          content: "Keep this active source unchanged."
        };
        const originalSource = { ...activeSource };
        const openedDocuments: TemplateDocumentSpec[] = [];

        await openSpecTemplate("feature_spec", {
          chooseFormat: async () => "md",
          loadCatalog: async () => catalog,
          openUntitledDocument: async (document) => {
            openedDocuments.push(document);
          }
        });

        assert.equal(openedDocuments.length, 1);
        assert.deepEqual(activeSource, originalSource);
        assert.notEqual(openedDocuments[0].content, activeSource.content);
      }
    },
    {
      name: "does not open a document when the format picker is cancelled",
      run: async () => {
        let loadedCatalog = false;
        let openedDocument = false;

        const result = await openSpecTemplate("feature_spec", {
          chooseFormat: async () => undefined,
          loadCatalog: async () => {
            loadedCatalog = true;
            return catalog;
          },
          openUntitledDocument: async () => {
            openedDocument = true;
          }
        });

        assert.equal(result, undefined);
        assert.equal(loadedCatalog, false);
        assert.equal(openedDocument, false);
      }
    }
  ]);
}
