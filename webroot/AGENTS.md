# Project Instructions

## General
- Consistency with existing code is of high importance. If it's not understood how to generate code without maintaining consistency then stop and ask how to proceed.

---

## Code Architecture
- When adding a new file, scan existing files of the same type (components, models, network, pages, etc.) and identify files with a similar context to try and reuse existing patterns.
- Every new JavaScript or TypeScript source file starts with the standard header comment block, matching the blueprint templates:
    ```
    //
    //  FileName.ts
    //  CompactConnect
    //
    //  Created by InspiringApps on M/D/YYYY.
    //
    ```
- Components, pages, and models are created with the blueprint CLI, which produces the correct 4-file structure and headers: `node blueprint create <component|page|model> <Name> <sub-path>`
- Components and pages are always 4 co-located files: `Name.vue`, `Name.ts`, `Name.less`, `Name.spec.ts`
- Class components use `vue-facing-decorator` and keep the blueprint's section comment order (`// PROPS`, `// Data`, `// Lifecycle`, `// Computed`, `// Methods`), exported via `toNative()`
- Always import via the path aliases defined in `vue.config.js` / `tsconfig.json` (`@/`, `@components`, `@models`, `@network`, `@pages`, `@plugins`, `@store`, `@tests`, `@router`, `@locales`, `@assets`), never deep relative paths
- If you ever try to add a new code pattern, prompt me first to confirm the addition of a new pattern.

---

## Code Style
- Always evaluate .eslintrc.js and run the linter after any code updates, fixing any issues.
- Always use strict equality (`===` / `!==`). Do not use `==` or `!=`, including `== null` / `!= null`.
- Always add a blank line after the last variable declaration in a block of variable declarations, even if there is only one variable.
- Always add a line break before return statements.
- Never use early returns.

### Code Style: TypeScript
- Follow existing typing conventions in code modules of similar types (components, models, network, pages, store, etc.).
- Prefer implementing typing where necessary, but do not add unnecessary type declarations if the compiler will be able to infer typing.
- Prefer to never use `any`
    - Rare exceptions include working with _some_ 3rd party libraries and globals, where typing would require extra bloat for minimal gain.
- Our approach to TypeScript is to use it as much as practical, but not at the expense of bloated or difficult-to-read code. Follow existing typing conventions.

### Code Style: Less
- Reuse variables and mixins from `src/styles.common/*` rather than hardcoding colors, spacing, or breakpoints
- Property order follows `stylelint-config-rational-order`; see `.stylelintrc.json`
- `yarn lint` does not run stylelint — it runs via the webpack plugin, so style violations only appear on `yarn serve` / `yarn build`

---

## Tests
- Always look at existing relevant test files to maintain consistency with sections, comments, variable naming, test naming, test ordering, test completeness, etc.
- Always look to keep test files organized and blocks grouped by similar tests.
- Try to keep tests to one request operation; e.g. preparing a state, calling a function, asserting the response / state.
- Within `describe()` blocks, do not add blank lines between `it()` cases.
- Tests should always be deterministic.
- Mount components with `mountShallow` / `mountFull` from `@tests/helpers/setup`; do not hand-roll mount config.
- `tests/helpers/setup.ts` provides a global `beforeEach`/`afterEach` that forces the `en` locale, recreates the `$api` sinon stub, calls. `sinon.restore()`, and unmounts tracked wrappers. Do not duplicate that teardown in specs.
- Console errors containing `Vue warn` or `unhandledRejection` fail the test. A mysterious failure is usually an unhandled prop / type warning, not a bad assertion.
- In the test environment `@network/data.api` is aliased to `src/network/mocks/mock.data.api`; tests never hit a real API
- When testing models, always follow the existing pattern of:
    - Test all fields and methods with expected defaults.
    - Test all fields and methods with specific values.
    - Test all fields and methods with specific values through serializer.
    - After those 3 core test cases, follow with any necessary specific state tests.

### Tests: `matchPattern()` assertions
- `chai-match-pattern`: Any spec using it must register it in-file:
    ```ts
    import chaiMatchPattern from 'chai-match-pattern';
    import chai from 'chai';
    chai.use(chaiMatchPattern);
    const { expect } = chai;
    ```
    - Note this replaces the blueprint's `import { expect } from 'chai'`.
- Use `to.matchPattern()` for whole array / object equality rather than chaining `lengthOf` plus per-index assertions.
- For nested structures assert the full expected shape inline, using `_.isInteger`, `_.isString`, etc. for dynamic values.
- When re-asserting nested objects across tests, spread from a stored fixture and override only what changed.

---

## Commands
- Package manager is yarn 1.x; never use `npm`.
- Lint check (what CI runs): `yarn lint --no-fix`.
- Lint with autofix: `yarn lint`.
- All unit tests: `yarn test:unit:all`.
- Targeted tests: `yarn test:unit <path-under-webroot>` (file or directory).
- A change is not done until `yarn lint --no-fix`, `yarn test:unit:all`, and `yarn build` all pass — these are the three steps in `.github/workflows/check-webroot.yml`.
- Do not silence lint failures with inline `eslint-disable`; prompt first.

---

## Internationalization
- No hardcoded user-facing strings; add keys to `src/locales/en.json` and reference via `$t` / `$tm`
- Key names must match exactly across all locale files. When adding a key to `en.json`, add the same key to `es.json` (an untranslated English value is acceptable; a missing key is not) — see `src/locales/readme.txt`

---

## Environment variables
- If environment variables are added / updated / removed, confirm that:
    - The `.env.example` file is up to date.
    - The `/src/plugins/EnvConfig` plugin is up to date.
    - The `.github/workflows/check-webroot.yml` is up to date.
    - The `Environment Configuration` section of the README is examined and flagged for updates if needed.
    - The backend files in `/backend/compact-connect-ui-app/` are up to date per the `Adding environment variables` section of the frontend README:
        - `cdk.context.*-example.json` files
        - `/stacks/frontend_deployment_stack/deployment.py`

---

## Content Security Policy (CSP)
- The CSP lives in `/backend/compact-connect-ui-app/lambdas/nodejs/cloudfront-csp/index.js` and is applied by a CloudFront lambda **only on deployed environments**. `yarn serve`, `yarn build`, and local `dist` testing have no CSP, so violations pass every local check and first appear on test / beta / prod. Reason about CSP impact from the code, not from local behavior.
- The policy is `default-src 'none'`, so any new external resource needs an explicit directive entry. Flag the user if a change involves:
    - A new third-party script or SDK → `script-src`, `script-src-elem`, usually `connect-src`, often `frame-src` and `style-src-elem` (see the recaptcha / authorize.net entries)
    - A new API, Cognito, or S3 host → `connect-src`
    - Images or media from a new host → `img-src` / `media-src`
    - `URL.createObjectURL()` or a `blob:` URL — `'self'` never matches `blob:`, so it must be listed explicitly in whichever directive consumes it:
        - `<img src="blob:…">` → `img-src`
        - `<audio>` / `<video src="blob:…">` → `media-src`
        - `<iframe src="blob:…">` → `frame-src`. Note the framed document inherits this CSP, so inline scripts / styles inside the generated HTML are still blocked by `default-src 'none'`.
        - `fetch()` / XHR against a `blob:` URL → `connect-src`
        - `new Worker(blobUrl)` → `worker-src`
        - `<object>` / `<embed>`, e.g. an inline PDF preview → blocked outright by `object-src 'none'`. Do not loosen it; use an `<iframe>` or a download instead.
        - `<a download href="blob:…">` plus `.click()` → needs **no** CSP change. A download is a navigation, and `default-src` is not a fallback for navigations. What may need `connect-src` is the API request that fetched the bytes, and that needs the API host, not `blob:`.
    - A new font source → `font-src` (currently only `self` and `fonts.gstatic.com`)
    - A web worker, or a change to the service worker / PWA manifest → `worker-src` / `manifest-src`
- Never propose `unsafe-inline`, `unsafe-eval`, `unsafe-hashes`, or `wasm-unsafe-eval`. `srcKeywordsEscape()` strips them with a console warning, so they will not work. If a third-party library injects an inline `<style>`, add its sha256 hash to `style-src-elem` instead.
- `form-action 'none'`: native form submission is blocked app-wide. All `<form>` elements must use `@submit.prevent` with a JS handler.
- `frame-ancestors 'none'` plus `X-Frame-Options: DENY`: the app cannot be embedded in an iframe.
- Environment-specific domains are injected at build time as `##PLACEHOLDER##` tokens by `generate_csp_lambda_code()` in `/stacks/frontend_deployment_stack/distribution.py`. Never hardcode an environment domain in the CSP — add a placeholder and its replacement mapping.
- A CSP change is cross-cutting and always requires prompting first. It also requires updating `cloudfront-csp/test/index.test.js` and regenerating four CDK snapshots — follow the `Updating the Content-Security-Policy (CSP) headers` section of the frontend README exactly.

---

## Documentation
- `README.md`
    - If code updates should also result in updates to the README, suggest any proposed edits.
    - Do not ever make updates without first prompting with the suggested updates.
- `AGENTS.md`
    - If an agent is having trouble executing a task, suggest any proposed edits to this AGENTS.md file.
    - Do not make updates without first prompting with the suggested updates.
- `/docs/ADD_COMPACT.md`
    - If code updates ever change the steps required for adding a compact in ADD_COMPACT.md, suggest any proposed updates.
    - Do not make updates without first prompting with the suggested updates.

---

### Ask Before
Prompt with a proposed approach before doing any of the following. If the run is non-interactive
and you cannot ask, take the most conservative option available, note it plainly in your summary,
and do not proceed with anything on this list that has no conservative fallback.

- Adding a new code pattern, or a new architectural layer / directory.
- Adding, upgrading, or removing a dependency, or otherwise changing `package.json` / `yarn.lock`.
- Silencing a check: inline `eslint-disable` / `stylelint-disable`, `@ts-ignore`, `@ts-expect-error`, or casting through `as any` to get past a type error.
- Weakening tests to get a suite passing: deleting or renaming existing tests, `it.skip` / `describe.skip`, removing assertions, or loosening an assertion to match current behavior.
- Changing shared test or build infrastructure: `tests/helpers/setup.ts`, `tests/mocks/*`, `.eslintrc.js`, `.stylelintrc.json`, `vue.config.js`, `tsconfig.json`, `babel.config.js`, `nyc.config.js`, or the `blueprints/*` templates.
- Changing auth, session, or token handling: `src/utils/auth.ts`, `src/router/_guards.ts`, the `AuthCallback` pages, or anything touching Cognito domains / client IDs.
- Changing route paths in `src/router/routes.ts` — URLs are a public contract.
- Changing a model serializer's server-side field mapping, which implies a backend contract change.
- Renaming or removing existing locale keys, which breaks in-flight translation bundles.
- Adding, renaming, or removing environment variables.
- Any change to the Content Security Policy.
- Editing `README.md`, `AGENTS.md`, or `/docs/ADD_COMPACT.md`.
- Touching anything outside `/webroot`.
- Running commands with side effects beyond the working tree: `git commit` / `git push`, `yarn install` in a way that rewrites the lockfile, or anything that deploys.
