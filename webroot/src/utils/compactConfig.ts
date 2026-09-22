//
//  compactConfig.ts
//  CompactConnect
//
//  Created by InspiringApps on 8/18/2026.
//

import { AppModes, AppGroupModes, psypactHostnames } from '@/app.config';
import { config as envConfig } from '@plugins/EnvConfig/envConfig.plugin';

export enum CompactType {
    ASLP = 'aslp',
    OT = 'octp',
    COUNSELING = 'coun',
    COSMETOLOGY = 'cosm',
    SOCIAL_WORK = 'socw',
    PSYPACT = 'psyp',
}

export interface CompactSetup {
    type: CompactType;
    appMode: AppModes;
    isEnabled: () => boolean; // Evaluated lazily as predicate function; so environment gating stays testable, resolved to a boolean by the Compacts plugin.
}

export const compactSetups: Record<CompactType, CompactSetup> = {
    [CompactType.ASLP]: {
        type: CompactType.ASLP,
        appMode: AppModes.JCC,
        isEnabled: () => true,
    },
    [CompactType.OT]: {
        type: CompactType.OT,
        appMode: AppModes.JCC,
        isEnabled: () => true,
    },
    [CompactType.COUNSELING]: {
        type: CompactType.COUNSELING,
        appMode: AppModes.JCC,
        isEnabled: () => true,
    },
    [CompactType.COSMETOLOGY]: {
        type: CompactType.COSMETOLOGY,
        appMode: AppModes.COSMETOLOGY,
        isEnabled: () => true,
    },
    [CompactType.SOCIAL_WORK]: {
        type: CompactType.SOCIAL_WORK,
        appMode: AppModes.SOCIAL_WORK,
        isEnabled: () => !envConfig.isAppProduction, // @NOTE: No Prod infra yet
    },
    [CompactType.PSYPACT]: {
        type: CompactType.PSYPACT,
        appMode: AppModes.PSYPACT,
        isEnabled: () => !envConfig.isAppProduction, // @NOTE: No Prod infra yet
    },
};

export const appModeGroups: Record<AppModes, AppGroupModes> = {
    [AppModes.JCC]: AppGroupModes.PRIVILEGE_PURCHASE,
    [AppModes.COSMETOLOGY]: AppGroupModes.MULTI_STATE,
    [AppModes.SOCIAL_WORK]: AppGroupModes.MULTI_STATE,
    [AppModes.PSYPACT]: AppGroupModes.MULTI_STATE,
};

export const getCompactSetup = (compactType?: CompactType | string | null): CompactSetup | null =>
    compactSetups[compactType as CompactType] || null;

export const getAppModeForCompact = (compactType?: CompactType | string | null): AppModes =>
    getCompactSetup(compactType)?.appMode || AppModes.JCC;

export const getAppGroupModeForAppMode = (appMode?: AppModes | null): AppGroupModes | null =>
    appModeGroups[appMode as AppModes] || null;

// =============================
// =   Host-pinned app modes   =
// =============================
// A single build is served at compact-specific hostnames, so the host decides the app mode.
export const appModeHostnames: Partial<Record<AppModes, Array<string>>> = {
    [AppModes.PSYPACT]: psypactHostnames,
};

export const isLocalHostname = (): boolean => ['localhost', '127.0.0.1'].includes(window.location.hostname);

export const getHostAppMode = (): AppModes | null => {
    const { hostname } = window.location;
    const hostMatch = Object.entries(appModeHostnames).find(([, hostnames]) => hostnames?.includes(hostname));

    return (hostMatch) ? (hostMatch[0] as AppModes) : null;
};

// Deployed compact-specific hosts never switch mode at run time; localhost stays switchable for dev & testing
export const getLockedAppMode = (): AppModes | null => {
    const isSwitchable = isLocalHostname() || envConfig.isAppLocal;

    return (isSwitchable) ? null : getHostAppMode();
};

// Most app modes map to a single compact; jcc spans several, so only resolve unambiguous modes
export const getSoleCompactForAppMode = (appMode?: AppModes | null): CompactType | null => {
    const compactTypes = Object.values(compactSetups)
        .filter((setup) => setup.appMode === appMode)
        .map((setup) => setup.type);

    return (compactTypes.length === 1) ? compactTypes[0] : null;
};

// =============================
// =     Encumbrance Types     =
// =============================
export interface EncumberConfig {
    disciplineTypes: Array<string>;
    npdbTypes: Array<string>;
}

export interface AppModeEncumberConfig {
    license: EncumberConfig;
    privilege: EncumberConfig;
}

// The surrender type is the only discipline type that differs between licenses and privileges
const disciplineTypesFull = (surrenderType: string): Array<string> => [
    'fine',
    'reprimand',
    'required supervision',
    'completion of continuing education',
    'public reprimand',
    'probation',
    'injunctive action',
    'suspension',
    'revocation',
    'denial',
    surrenderType,
    'modification of previous action-extension',
    'modification of previous action-reduction',
    'other monitoring',
    'other adjudicated action not listed',
];
const disciplineTypesCosmetology = (surrenderType: string): Array<string> => [
    'suspension',
    'revocation',
    surrenderType,
];
const npdbTypesFull = [
    'Non-compliance With Requirements',
    'Conflict of Interest',
    'Substandard Care or Patient Neglect/Abuse',
    'Criminal Conviction or Adjudication',
    'Confidentiality, Consent or Disclosure Violations',
    'Fraud, Deception, or Misrepresentation',
    'Improper Supervision or Allowing Unlicensed Practice',
    'Improper Prescribing, Dispensing, Administering Medication/Drug Violation',
    'Other',
];
const npdbTypesJcc = [
    'Non-compliance With Requirements',
    'Criminal Conviction or Adjudication',
    'Confidentiality, Consent or Disclosure Violations',
    'Misconduct or Abuse',
    'Fraud, Deception, or Misrepresentation',
    'Unsafe Practice or Substandard Care',
    'Improper Supervision or Allowing Unlicensed Practice',
    'Other',
];
const npdbTypesCosmetology = [
    'fraud',
    'consumer harm',
    'other',
];

export const appModeEncumberConfigs: Record<AppModes, AppModeEncumberConfig> = {
    [AppModes.JCC]: {
        license: {
            disciplineTypes: disciplineTypesFull('surrender of license'),
            npdbTypes: npdbTypesJcc,
        },
        privilege: {
            disciplineTypes: disciplineTypesFull('surrender of privilege'),
            npdbTypes: npdbTypesJcc,
        },
    },
    [AppModes.COSMETOLOGY]: {
        license: {
            disciplineTypes: disciplineTypesCosmetology('surrender of license'),
            npdbTypes: npdbTypesCosmetology,
        },
        privilege: {
            disciplineTypes: disciplineTypesCosmetology('surrender of privilege'),
            npdbTypes: npdbTypesCosmetology,
        },
    },
    [AppModes.SOCIAL_WORK]: {
        license: {
            disciplineTypes: disciplineTypesFull('surrender of license'),
            npdbTypes: npdbTypesFull,
        },
        privilege: {
            disciplineTypes: disciplineTypesFull('surrender of privilege'),
            npdbTypes: npdbTypesFull,
        },
    },
    [AppModes.PSYPACT]: {
        license: {
            disciplineTypes: disciplineTypesFull('surrender of license'),
            npdbTypes: npdbTypesFull,
        },
        privilege: {
            disciplineTypes: disciplineTypesFull('surrender of privilege'),
            npdbTypes: npdbTypesFull,
        },
    },
};

export const getEncumberConfigLicense = (appMode: AppModes): EncumberConfig =>
    appModeEncumberConfigs[appMode]?.license || { disciplineTypes: [], npdbTypes: [] };

export const getEncumberConfigPrivilege = (appMode: AppModes): EncumberConfig =>
    appModeEncumberConfigs[appMode]?.privilege || { disciplineTypes: [], npdbTypes: [] };
