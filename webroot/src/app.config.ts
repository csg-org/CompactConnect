//
//  app.config.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 4/27/21.
//
import localStorage from '@store/local.storage';

// =========================
// =  Authorization Types  =
// =========================
export enum AuthTypes {
    STAFF = 'staff',
    LICENSEE = 'licensee',
    PUBLIC = 'public',
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
// =   Auth storage   =
// ====================
export const authStorage = localStorage;
export const tokens = {
    staff: {
        AUTH_TOKEN: 'auth_token_staff',
        AUTH_TOKEN_TYPE: 'auth_token_type_staff',
        AUTH_TOKEN_EXPIRY: 'auth_token_expiry_staff',
        ID_TOKEN: 'id_token_staff',
        REFRESH_TOKEN: 'refresh_token_staff',
    },
    licensee: {
        AUTH_TOKEN: 'auth_token_licensee',
        AUTH_TOKEN_TYPE: 'auth_token_type_licensee',
        AUTH_TOKEN_EXPIRY: 'auth_token_expiry_licensee',
        ID_TOKEN: 'id_token_licensee',
        REFRESH_TOKEN: 'refresh_token_licensee',
    },
};
export const AUTH_TYPE = 'auth_type';
export const AUTH_LOGIN_GOTO_PATH = 'login_goto';
export const AUTH_LOGIN_GOTO_PATH_AUTH_TYPE = 'login_goto_auth_type';

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
};

export default {
    authStorage,
    tokens,
    AUTH_LOGIN_GOTO_PATH,
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
