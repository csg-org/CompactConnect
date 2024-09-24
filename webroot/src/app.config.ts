//
//  app.config.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 4/27/21.
//
import sessionStorage from '@store/session.storage';

// ====================
// =   Auth storage   =
// ====================
export const authStorage = sessionStorage;
export const tokens = {
    staff: {
        AUTH_TYPE: 'auth_type',
        AUTH_TOKEN: 'auth_token_staff',
        AUTH_TOKEN_TYPE: 'auth_token_type_staff',
        AUTH_TOKEN_EXPIRY: 'auth_token_expiry_staff',
        ID_TOKEN: 'id_token_staff',
        REFRESH_TOKEN: 'refresh_token_staff',
    },
    licensee: {
        AUTH_TYPE: 'auth_type',
        AUTH_TOKEN: 'auth_token_licensee',
        AUTH_TOKEN_TYPE: 'auth_token_type_licensee',
        AUTH_TOKEN_EXPIRY: 'auth_token_expiry_licensee',
        ID_TOKEN: 'id_token_licensee',
        REFRESH_TOKEN: 'refresh_token_licensee',
    },
};
export const AUTH_LOGIN_GOTO_PATH = 'login_goto';

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

// =============================
// =  Authorization Types        =
// =============================
export enum AuthTypes {
    STAFF = 'staff',
    LICENSEE = 'licensee'
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
// =  Compact configuration    =
// =============================
export const compacts = {
    aslp: {
        memberStates: [
            'AL',
            'AK',
            'AR',
            'CO',
            'DE',
            'FL',
            'GA',
            'ID',
            'IN',
            'IA',
            'KS',
            'KY',
            'LA',
            'ME',
            'MD',
            'MN',
            'MS',
            'MO',
            'MT',
            'NE',
            'NH',
            'NC',
            'OH',
            'OK',
            'SC',
            'TN',
            'UT',
            'VT',
            'VA',
            'WA',
            'WV',
            'WI',
            'WY',
        ],
    },
    octp: {
        memberStates: [
            'AL',
            'AZ',
            'AR',
            'CO',
            'DE',
            'GA',
            'IN',
            'IA',
            'KY',
            'LA',
            'ME',
            'MD',
            'MN',
            'MS',
            'MO',
            'MT',
            'NE',
            'NH',
            'NC',
            'OH',
            'SC',
            'SD',
            'TN',
            'UT',
            'VT',
            'VA',
            'WA',
            'WV',
            'WI',
            'WY',
        ],
    },
    coun: {
        memberStates: [
            'AL',
            'AZ',
            'AR',
            'CO',
            'CT',
            'DE',
            'FL',
            'GA',
            'IN',
            'IA',
            'KS',
            'KY',
            'LA',
            'ME',
            'MD',
            'MN',
            'MS',
            'MO',
            'MT',
            'NE',
            'NH',
            'NJ',
            'NC',
            'ND',
            'OH',
            'OK',
            'SC',
            'SD',
            'TN',
            'UT',
            'VT',
            'VA',
            'WA',
            'WV',
            'WI',
            'WY',
        ],
    },
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
