//
//  app.config.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 4/27/21.
//

// ===============
// =  App Modes  =
// ===============
export enum AppModes {
    JCC = 'jcc',
    COSMETOLOGY = 'cosmo',
    SOCIAL_WORK = 'social-work',
    PRIVILEGE_PURCHASE = 'privilege-purchase',
    MULTI_STATE = 'multi-state',
}

export enum AppGroupModes {
    PRIVILEGE_PURCHASE = 'privilege-purchase',
    MULTI_STATE = 'multi-state',
}

// =========================
// =   Permission Types    =
// =========================
export enum Permission {
    NONE = 'none',
    READ_PRIVATE = 'readPrivate',
    READ_SSN = 'readSSN',
    WRITE = 'write',
    ADMIN = 'admin',
}

// =========================
// =       Fee Types       =
// =========================
export enum FeeTypes {
    FLAT_RATE = 'FLAT_RATE',
    FLAT_FEE_PER_PRIVILEGE = 'FLAT_FEE_PER_PRIVILEGE'
}

// ====================
// =  User Languages  =
// ====================
export const languagesEnabled = [
    { value: 'en', name: 'English' },
    { value: 'es', name: 'Español' },
];

export const getBrowserLanguage = () => {
    const browserDefault = window.navigator.language;
    let browserLanguage = 'en';

    if (browserDefault) {
        languagesEnabled.forEach((language) => {
            const languageValue = language.value;
            const isGenericLanguageFound = browserDefault.startsWith(languageValue);
            const isRegionalLanguageFound = browserDefault.startsWith(`${languageValue}-`);

            if (isGenericLanguageFound || isRegionalLanguageFound) {
                browserLanguage = languageValue;
            }
        });
    }

    return browserLanguage;
};

export const defaultLanguage = getBrowserLanguage();

// =============================
// =     Server API Types      =
// =============================
export enum ServerApiTypes {
    API_EXAMPLE = 'Example',
}

export enum MilitaryAuditStatusTypes {
    NOT_APPLICABLE = 'notApplicable',
    APPROVED = 'approved',
    DECLINED = 'declined',
    TENTATIVE = 'tentative',
}

// =============================
// =    Server Date Formats    =
// =============================
export const serverDateFormat = 'YYYY-MM-DD';
export const serverDatetimeFormat = 'YYYY-MM-DDTHH:mm:ss.SSS';

// =============================
// =   Display Date Formats    =
// =============================
export const displayDateFormat = 'M/D/YYYY';
export const displayDatetimeFormat = 'M/D/YYYY h:mm a';

// =============================
// =   Date Format Patterns    =
// =============================
export const dateFormatPatterns = {
    MM_DD_YYYY: /^\d{2}\/\d{2}\/\d{4}$/,
    YYYY_MM_DD: /^\d{4}-\d{2}-\d{2}$/,
};

// =============================
// =   Relative Time Formats   =
// =============================
export const relativeTimeFormats = {
    future: 'in %s',
    past: '%s ago',
    s: 'Now',
    ss: 'Now',
    m: '%dm',
    mm: '%dm',
    h: '%dh',
    hh: '%dh',
    d: '%dd',
    dd: '%dd',
    M: '%dmo',
    MM: '%dmo',
    y: '%dy',
    yy: '%dy'
};

// =============================
// =  Upload File Types        =
// =============================
export enum UploadFileType {
    DATA = 'data',
    IMAGE = 'image',
    DOCUMENT = 'document',
}

export interface InterfaceUploadFile {
    mime: string;
    ext: string;
    type: UploadFileType,
}

export const uploadTypes = {
    CSV: <InterfaceUploadFile> {
        mime: `text/csv`,
        ext: `.csv`,
        type: UploadFileType.DATA,
    }
};

// =============================
// =         State List        =
// =============================
export const stateList = [
    'AL',
    'AK',
    'AZ',
    'AR',
    'CA',
    'CO',
    'CT',
    'DE',
    'DC',
    'FL',
    'GA',
    'HI',
    'ID',
    'IL',
    'IN',
    'IA',
    'KS',
    'KY',
    'LA',
    'ME',
    'MD',
    'MA',
    'MI',
    'MN',
    'MS',
    'MO',
    'MT',
    'NE',
    'NV',
    'NH',
    'NJ',
    'NM',
    'NY',
    'NC',
    'ND',
    'OH',
    'OK',
    'OR',
    'PA',
    'RI',
    'SC',
    'SD',
    'TN',
    'TX',
    'UT',
    'VT',
    'VA',
    'WA',
    'WV',
    'WI',
    'WY',
    'AS',
    'GU',
    'MP',
    'PR',
    'VI'
];

// =============================
// =  Compact configuration    =
// =============================
export const compacts = {
    aslp: {},
    octp: {},
    coun: {},
    cosm: {},
};

// =============================
// =     Feature gate IDs      =
// =============================
export enum FeatureGates {
    EXAMPLE_FEATURE_1 = 'test-feature-1', // Keep this ID in place for examples & tests
}

export default {
    AppModes,
    AppGroupModes,
    Permission,
    FeeTypes,
    languagesEnabled,
    defaultLanguage,
    serverDateFormat,
    serverDatetimeFormat,
    displayDateFormat,
    displayDatetimeFormat,
    relativeTimeFormats,
    UploadFileType,
    uploadTypes,
    compacts,
};
