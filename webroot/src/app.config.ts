//
//  app.config.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 4/27/21.
//

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

export const mobileStoreLinks = {
    APPLE_STORE_LINK: '/',
    GOOGLE_STORE_LINK: '/',
};

// =============================
// =  Upload File Extensions   =
// =============================
export const uploadImageExtensions = [
    '.bmp',
    '.gif',
    '.jpeg',
    '.jpg',
    '.png',
    '.tif',
    '.tiff',
];

export const uploadDataExtensions = [
    '.csv',
    '.tsv',
    '.pdf',
    '.txt',
    '.xls',
    '.xml',
    '.xlsx',
];

export default {
    languagesEnabled,
    defaultLanguage,
    serverDateFormat,
    serverDatetimeFormat,
    displayDateFormat,
    displayDatetimeFormat,
    relativeTimeFormats,
    mobileStoreLinks,
    uploadImageExtensions,
    uploadDataExtensions,
};
