//
//  _helpers.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 4/12/20.
//

import {
    serverDatetimeFormat,
    serverDateFormat,
    displayDateFormat,
    displayDatetimeFormat
} from '@/app.config';
import moment from 'moment';

type stringOptional = string | null | undefined;

/**
 * Generic date / datetime display formatter.
 * @param  dateString    The server date / datetime string.
 * @param  displayFormat The output display format (momentjs).
 * @return               The display-formatted string.
 */
const displayFormat = (dateString: stringOptional, outFormat: string): string => {
    const possibleInputFormats = [
        serverDatetimeFormat,
        serverDateFormat,
    ];
    let display = '';

    if (dateString) {
        display = moment.utc(dateString, possibleInputFormats).local().format(outFormat);
    }

    return display;
};

/**
 * Convert server datetime / date to date display format.
 * @param  dateString The server date / datetime string.
 * @return            The date display-formatted string.
 */
const dateDisplay = (dateString: stringOptional): string => displayFormat(dateString, displayDateFormat);

/**
 * Convert server datetime / date to datetime display format.
 * @param  dateString The server date / datetime string.
 * @return            The datetime display-formatted string.
 */
const datetimeDisplay = (dateString: stringOptional): string => displayFormat(dateString, displayDatetimeFormat);

/**
 * Convert server datetime / date to relative display format.
 * @param  dateString The server date / datetime string.
 * @return            The datetime display-formatted string.
 */
const relativeFromNowDisplay = (dateString: stringOptional): string => {
    const possibleInputFormats = [
        serverDatetimeFormat,
        serverDateFormat,
    ];
    let display = '';

    if (dateString) {
        display = moment.utc(dateString, possibleInputFormats).local().fromNow(true);
    }

    return display;
};

export {
    dateDisplay,
    datetimeDisplay,
    relativeFromNowDisplay
};
