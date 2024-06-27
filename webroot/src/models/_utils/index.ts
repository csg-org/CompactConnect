export interface InterfaceBrowserInfo {
    name: string;
    version: string;
}

// https://developer.mozilla.org/en-US/docs/Web/HTTP/Browser_detection_using_the_user_agent
export const getBrowserInfo = (): InterfaceBrowserInfo => {
    const { userAgent } = navigator;
    const enum browsers {
        CHROME = 'Chrome',
        CHROMIUM = 'Chromium',
        FIREFOX = 'Firefox',
        SAFARI = 'Safari',
        EDGE = 'Edge',
        IE = 'Internet Explorer',
        OPERA = 'Opera',
        SEAMONKEY = 'Seamonkey',
    }
    const browsersList = [
        browsers.CHROME,
        browsers.CHROMIUM,
        browsers.FIREFOX,
        browsers.SAFARI,
        browsers.EDGE,
        browsers.IE,
        browsers.OPERA,
        browsers.SEAMONKEY,
    ];
    const browserInfo: InterfaceBrowserInfo = {
        name: 'unknown',
        version: 'unknown',
    };
    const getBrowserVersion = (browserNameIndex: number) => {
        let version = 'unknown';
        const userAgentSubstring = userAgent.substring(browserNameIndex);
        const versionSubstring = userAgentSubstring.split(' ')[0];
        const versionArray = versionSubstring.split('/');

        if (versionArray.length > 1) {
            [ , version ] = versionArray; // versionArray[1];
        }

        return version;
    };
    const getIEVersion = (browserNameIndex: number, browserKeyword: string) => {
        let versionSubstring = '';
        let versionArray: Array<string> = [];
        let version = 'unknown';

        const userAgentSubstring = userAgent.substring(browserNameIndex);

        if (browserKeyword === 'MSIE') {
            [ versionSubstring ] = userAgentSubstring.split(';');
            versionArray = versionSubstring.split(' ');

            if (versionArray.length > 1) {
                [ , version ] = versionArray; // versionArray[1]
            }
        } else {
            // browserKeyword === 'rv:'
            [ versionSubstring ] = userAgentSubstring.split(')');
            versionArray = versionSubstring.split(':');

            if (versionArray.length > 1) {
                [ , version ] = versionArray; // versionArray[1]
            }
        }
        return version;
    };
    const identifyBrowser = (browserName: string) => {
        switch (browserName) {
        case browsers.CHROME:
        case browsers.CHROMIUM:
        case browsers.SAFARI:
        case browsers.EDGE: {
            const chromeIndex = userAgent.indexOf(browsers.CHROME);
            const chromiumIndex = userAgent.indexOf(browsers.CHROMIUM);
            const safariIndex = userAgent.indexOf(browsers.SAFARI);
            const edgeIndex = userAgent.indexOf(browsers.EDGE);
            const edgIndex = userAgent.indexOf('Edg');

            if (safariIndex > -1 && chromeIndex < 0 && chromiumIndex < 0) {
                browserInfo.name = browsers.SAFARI;
                browserInfo.version = getBrowserVersion(safariIndex);
            } else if (chromeIndex > -1 && chromiumIndex < 0 && edgeIndex < 0 && edgIndex < 0) {
                browserInfo.name = browsers.CHROME;
                browserInfo.version = getBrowserVersion(chromeIndex);
            } else if (chromeIndex < 0 && chromiumIndex > -1) {
                browserInfo.name = browsers.CHROMIUM;
                browserInfo.version = getBrowserVersion(chromiumIndex);
            } else if (edgeIndex > -1 || edgIndex > -1) {
                browserInfo.name = browsers.EDGE;
                const index = (edgeIndex > -1) ? edgeIndex : edgIndex;

                browserInfo.version = getBrowserVersion(index);
            }
            break;
        }
        case browsers.FIREFOX:
        case browsers.SEAMONKEY: {
            const firefoxIndex = userAgent.indexOf(browsers.FIREFOX);
            const seamonkeyIndex = userAgent.indexOf(browsers.SEAMONKEY);

            if (firefoxIndex > -1 && seamonkeyIndex < 0) {
                browserInfo.name = browsers.FIREFOX;
                browserInfo.version = getBrowserVersion(firefoxIndex);
            } else if (seamonkeyIndex > -1) {
                browserInfo.name = browsers.SEAMONKEY;
                browserInfo.version = getBrowserVersion(seamonkeyIndex);
            }
            break;
        }
        case browsers.OPERA: {
            const operaIndex = userAgent.indexOf(browsers.OPERA);
            const oprIndex = userAgent.indexOf('OPR/');

            if (operaIndex > -1 || oprIndex > -1) {
                browserInfo.name = browsers.OPERA;
                const idx = (operaIndex > -1) ? operaIndex : oprIndex;

                browserInfo.version = getBrowserVersion(idx);
            }
            break;
        }
        case browsers.IE: {
            const ieMSIEIndex = userAgent.indexOf('MSIE');
            const ieTridentIndex = userAgent.indexOf('Trident');
            const ieRVIndex = userAgent.indexOf('rv:');
            const ieIndex = (ieMSIEIndex > -1) ? ieMSIEIndex : ieRVIndex;
            const browserKeyword = (ieMSIEIndex > -1) ? 'MSIE' : 'rv:';

            if (ieMSIEIndex > -1 || ieTridentIndex > -1 || ieRVIndex > -1) {
                browserInfo.name = browsers.IE;
                browserInfo.version = getIEVersion(ieIndex, browserKeyword);
            }
            break;
        }
        default:
            browserInfo.name = 'unknown';
            browserInfo.version = 'unknown';
        }
    };

    browsersList.forEach((browser) => {
        if (browserInfo.name === 'unknown') {
            identifyBrowser(browser);
        }
    });

    return browserInfo;
};

// https://developer.mozilla.org/en-US/docs/Web/HTTP/Browser_detection_using_the_user_agent
export const getDeviceType = (): string => {
    let deviceType = 'unknown';

    if (navigator.userAgent.indexOf('Mobi') > -1) {
        deviceType = 'Mobile';
    } else {
        deviceType = 'Desktop';
    }

    return deviceType;
};

export default {
    getBrowserInfo,
    getDeviceType,
};
