/**
 * Function signature for one synchronous unit test.
 */
export type TestCase = {
  name: string;
  run: () => void;
};

/**
 * Runs a small dependency-free test suite so extension logic can be tested even
 * on Node versions that do not support `node --test`.
 */
export function runSuite(name: string, tests: TestCase[]): void {
  console.log(`\n${name}`);
  for (const test of tests) {
    try {
      test.run();
      console.log(`  ✓ ${test.name}`);
    } catch (error) {
      process.exitCode = 1;
      console.error(`  ✗ ${test.name}`);
      console.error(error);
    }
  }
}
