# Adding a new compact (new AppMode)

## Prerequisites

- Backend API hosts and staff Cognito app exist (or are being added in parallel)
- Cognito callback URL(s) will be registered for the new staff auth path
- Choose an existing `AppGroupMode`:
  - `PRIVILEGE_PURCHASE` (JCC-style)
  - `MULTI_STATE` (cosmetology / social work–style)
- One compact maps to one `AppModes` value
- Staff Cognito is per AppMode; licensee Cognito is shared unless product requirements change

## Naming

| Concept | Example | Notes |
|---------|---------|--------|
| `CompactType` value | `foo` | API / locale key (`compacts[].key`, license `compactKey`) |
| `AppModes` value | `foo` | **Must** equal the auth callback path segment |

Auth callback path is built as:

`/auth/callback/staff/{AppModes value}`

Example: `AppModes.FOO = 'foo'` → `/auth/callback/staff/foo`

## Already automatic

Once the config and infra wiring below are in place, these do **not** need per-compact UI lists or interceptor edits:

- PublicDashboard staff login cards (`$compactsEnabled`)
- CompactSelector (public + permission-based options)
- Logout, token refresh, and token revoke (`getCognitoConfig`)
- Auth callback path string (`getAuthCallbackPath`)
- Network request base URLs (`getApiBaseUrl` + API interceptors)
- `setAppMode` → `appGroupMode` (`getAppGroupModeForAppMode`)
- Router compact param → app mode (`getAppModeForCompact`)

## Steps

### 1. Core enums and compact config

**`src/app.config.ts`**

- [ ] Add `AppModes.YOUR_MODE = 'yoursegment'`

**`src/utils/compactConfig.ts`**

- [ ] Add `CompactType.YOUR_COMPACT = 'abbr'`
- [ ] Add `compactSetups` entry (`type`, `appMode`, `isEnabled`)
- [ ] Add `appModeGroups[AppModes.YOUR_MODE]` → existing `PRIVILEGE_PURCHASE` or `MULTI_STATE`
- [ ] Add `appModeEncumberConfigs[AppModes.YOUR_MODE]` (license + privilege discipline / NPDB lists; reuse shared helpers when possible)

### 2. Environment

**`.env` / `.env.example`**

- [ ] Four API roots for the new mode: state, license, search, user
- [ ] Staff Cognito auth domain + client id

**`src/plugins/EnvConfig/envConfig.plugin.ts`**

- [ ] Add fields on `EnvConfig`
- [ ] Map them from `VUE_APP_*` keys

**`tests/mocks/mockEnvConfig.ts`**

- [ ] Add matching mock fields

### 3. Wire mode → infra tables

**`src/network/apiUrls.ts`**

- [ ] Add a row to `appModeApiUrls` for all four API families (`state`, `license`, `search`, `user`)  
  (`Record<AppModes, …>` will fail to compile until this is done.)

**`src/utils/auth.ts` → `getCognitoConfig`**

- [ ] Add a staff branch for the new `AppModes` that reads the new env Cognito fields

### 4. Auth callback route and page

**`src/router/routes.ts`**

- [ ] Add route `/auth/callback/staff/{yoursegment}`  
  Path must equal `getAuthCallbackPath(AppModes.YOUR_MODE, AuthTypes.STAFF)`

**`src/pages/AuthCallback/StaffYourMode/`**

- [ ] Add a thin page (copy `StaffCosmo` / `StaffSocialWork` pattern)
- [ ] Set `appMode = AppModes.YOUR_MODE` and `authType = AuthTypes.STAFF` only
- [ ] Add a mount spec (optional; matches existing AuthCallback pages)

**`src/router/router.spec.ts`**

- [ ] Add `{ name, path: getAuthCallbackPath(...) }` for the new staff callback route

### 5. Store and Compacts plugin flags

**`src/store/global/global.getters.ts`**

- [ ] Add `isAppModeYourMode: (state) => state.appMode === AppModes.YOUR_MODE`

**`src/plugins/Compacts/compacts.plugin.ts`**

- [ ] Add `'isAppModeYourMode'` to `appModeFlags`

**`src/plugins/Compacts/compacts.d.ts`**

- [ ] Declare `$isAppModeYourMode: boolean`

### 6. i18n / product copy

**`src/locales/en.json` and `src/locales/es.json`**

- [ ] Add `compacts[]` entry (`key` = `CompactType` value, `name`, `abbrev`)
- [ ] Add `licensing.licenseTypes` entries with matching `compactKey` as needed

### 7. Mock data

**`src/network/mocks/mock.data.ts`**

Needed when exercising the new compact under the mock API:

- [ ] Add a `staffAccount.permissions` entry keyed by the new `CompactType` value (mirror `aslp` / `cosm` / `socw`)
- [ ] Add the same key on any other mock staff permission blobs in this file that list every compact
- [ ] If the compact **allows licensee registration**, add it to `compactStatesForRegistration`  
  (Cosmetology and social work are omitted there on purpose because they do not allow registration.)
- [ ] Add or extend licensee / search fixtures only if you need mock flows for that compact (many fixtures stay on `octp` by default)

### 8. Optional / situational UI

Only if the new compact should participate in these flows:

**`src/pages/PublicDashboard/PublicDashboard.ts` → `bypassRedirect`**

- [ ] Add a `?bypass=login-staff-…` case if emails or deep links need it (see cosmo / social work)

**`RegisterLicensee` / `MfaResetStartLicensee`**

- [ ] These still use hard-coded compact allow-lists — add the new `CompactType` only if those pages should offer it

**Mode-specific UI audit**

Decide whether behavior should follow JCC-like or multi-state-like patterns. Prefer `$isAppGroupMode*` when the behavior is really group-scoped. Audit existing `$isAppModeJcc` / `$isAppModeCosmetology` / `$isAppModeSocialWork` usages, for example:

- LicenseCard / PrivilegeCard
- LicensingDetail (e.g. military affiliation)
- LicenseeSearchLegacy
- UserInvite / UserRowEdit

### 9. Tests to extend

- [ ] `src/utils/compactConfig.spec.ts` — setup, app group, encumbrance, enablement gating
- [ ] `src/network/apiUrls.spec.ts` — all four families for the new mode
- [ ] `src/plugins/Compacts/compacts.spec.ts` — list membership / globals if asserted
- [ ] `src/pages/PublicDashboard/PublicDashboard.spec.ts` — staff login URI for the new mode (optional)
- [ ] LicenseCard / PrivilegeCard encumber specs if per-mode assertions are kept there
- [ ] AuthCallback mount + router path consistency
