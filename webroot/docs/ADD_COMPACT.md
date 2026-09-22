# Adding a new compact (new AppMode)

_[Go to Steps](#steps)_

## Prerequisites

- Backend API hosts and staff Cognito app exist (or are being added in parallel)
- Cognito callback URLs for the new staff auth servers; and if practitioners are allowed to register, a URL for that as well
- Choose an existing `AppGroupMode`:
  - `PRIVILEGE_PURCHASE` (JCC-style)
  - `MULTI_STATE` (cosmetology / social work / psypact–style)
- One new compact usually maps to one `AppModes` value

## Naming

| Concept | Example | Notes |
|---------|---------|--------|
| `CompactType` value | `socialwork` | API / locale key (`compacts[].key`, license `compactKey`) |
| `AppModes` value | `socialwork` | **Must** equal the auth callback path segment |

Auth callback path is built as:

`/auth/callback/staff/{AppModes value}`

Example: `AppModes.SOCIAL_WORK = 'socialwork'` → `/auth/callback/staff/socialwork`

## Already automatic

Once the config and infra wiring below are in place, these do **not** need per-compact UI lists or interceptor edits:

- PublicDashboard staff login cards (`$compactsEnabledCompactConnect`; `$compactsEnabled` includes host-pinned compacts like psypact)
- CompactSelector (public + permission-based options)
- Logout, token refresh, and token revoke (`getCognitoConfig`)
- Auth callback path string (`getAuthCallbackPath`)
- Network request base URLs (`getApiBaseUrl` + API interceptors)
- `setAppMode` → `appGroupMode` (`getAppGroupModeForAppMode`)
- Router compact param → app mode (`getAppModeForCompact`)

---

## Steps

### 1. Environment

**`.env` / `.env.example`**

- [ ] Add the four API roots for the new mode: state, license, search, user
- [ ] Add the Staff Cognito auth domain + client id
- [ ] Add the Practitioner / Licensee Cognito auth domain + client id (if needed)

**`src/plugins/EnvConfig/envConfig.plugin.ts`**

- [ ] Add fields on `EnvConfig`
- [ ] Map them from `VUE_APP_*` keys

**`tests/mocks/mockEnvConfig.ts`**

- [ ] Add matching mock fields

### 2. Core enums and compact config

**`src/app.config.ts`**

- [ ] Add `AppModes.YOUR_MODE = 'yourmode'`

**`src/utils/compactConfig.ts`**

- [ ] Add `CompactType.YOUR_COMPACT = 'abbr'`
- [ ] Add `compactSetups` entry (`type`, `appMode`, `isEnabled`)
- [ ] Add `appModeGroups[AppModes.YOUR_MODE]` → existing `PRIVILEGE_PURCHASE` or `MULTI_STATE`
- [ ] Add `appModeEncumberConfigs[AppModes.YOUR_MODE]` (license + privilege discipline / NPDB lists; reuse shared helpers when possible)

**`src/utils/compactConfig.spec.ts`**

- [ ] Setup, app group, encumbrance, enablement gating

### 3. Network config

**`src/network/apiUrls.ts`**

- [ ] Add a row to `appModeApiUrls` for all four API families (`state`, `license`, `search`, `user`)  
  (`Record<AppModes, …>` will fail to compile until this is done.)

**`src/network/apiUrls.spec.ts`**

- [ ] All four families for the new mode

**`src/utils/auth.ts` → `getCognitoConfig`**

- [ ] Add a staff branch for the new `AppModes` that reads the new env Cognito fields

### 4. Auth callback route and page

**`src/pages/AuthCallback/{StaffYourMode}/`**

- [ ] Add a thin page (copy `StaffCosmo` / `StaffSocialWork` pattern)
- [ ] Set `appMode = AppModes.YOUR_MODE` and `authType = AuthTypes.STAFF` only
- [ ] Add a mount spec (optional; matches existing AuthCallback pages)

**`src/pages/AuthCallback/{LicenseeYourMode}/`** _(only if new compact supports licensee login)_

- [ ] Add a thin page (copy `LicenseeJcc` pattern)
- [ ] Set `appMode = AppModes.YOUR_MODE` and `authType = AuthTypes.LICENSEE` only
- [ ] Add a mount spec (optional; matches existing AuthCallback pages)

**`src/router/routes.ts`**

- [ ] Add route `/auth/callback/staff/{yoursegment}`
  Path must equal `getAuthCallbackPath(AppModes.YOUR_MODE, AuthTypes.STAFF)`
- [ ] Add route `/auth/callback/licensee/{yoursegment}` _(only if new compact supports licensee login)_
    Path must equal `getAuthCallbackPath(AppModes.YOUR_MODE, AuthTypes.STAFF)`

**`src/router/router.spec.ts`**

- [ ] Add `{ name, path: getAuthCallbackPath(...) }` for the new staff callback route

### 5. Store and Compacts plugin flags

**`src/store/global/global.getters.ts`**

- [ ] Add `isAppModeYourMode: (state) => state.appMode === AppModes.YOUR_MODE`

**`src/plugins/Compacts/compacts.plugin.ts`**

- [ ] Add `'isAppModeYourMode'` to `appModeFlags`

**`src/plugins/Compacts/compacts.d.ts`**

- [ ] Declare `$isAppModeYourMode: boolean`

**`src/plugins/Compacts/compacts.spec.ts`**

- [ ] List membership / globals if asserted

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
- [ ] If the new compact should have a different app mode in a public context, update the `get appTypeOptions()` computed and `handleAppTypeSelect()` method.

**`src/pages/PublicDashboard/PublicDashboard.spec.ts`**

- [ ] Staff login URI for the new mode (optional)

**`RegisterLicensee` / `MfaResetStartLicensee`**

- [ ] These still use hard-coded compact allow-lists — add the new `CompactType` only if those pages should offer it

**Host-pinned compacts** _(only if the compact gets its own DNS domains)_

- [ ] Add the hostnames to `app.config.ts` and register them in `appModeHostnames` (`src/utils/compactConfig.ts`)
- [ ] Register each hostname's `/auth/callback/...` and `/Logout` URLs on that compact's Cognito app clients
- [ ] Exclude the compact from `$compactsEnabledCompactConnect` if it should not appear in CompactConnect compact pickers

Deployed pinned hosts refuse routes for any other compact and ignore run-time `setAppMode` calls (`getLockedAppMode`); localhost stays switchable so the PublicDashboard app-type selector still works.

**Mode-specific UI audit**

Decide whether behavior should follow JCC-like or multi-state-like patterns. Prefer `$isAppGroupMode*` when the behavior is really group-scoped. Audit existing `$isAppModeJcc` / `$isAppModeCosmetology` / `$isAppModeSocialWork` usages, for example:

- LicenseCard / PrivilegeCard
- LicenseCard / PrivilegeCard encumber specs if per-mode assertions are kept there
- LicensingDetail (e.g. military affiliation)
- LicenseeSearchLegacy
- UserInvite / UserRowEdit

---
