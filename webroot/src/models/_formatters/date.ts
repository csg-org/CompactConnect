//
//  date.ts
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
import moment, { Moment, unitOfTime } from 'moment';

type stringOptional = string | null | undefined;

/**
 * Generic date / datetime display formatter.
 * @param  {string}  dateString           The server date / datetime string.
 * @param  {string}  displayFormat        The output display format (momentjs).
 * @param  {boolean} [skipTimezone=false] TRUE if no UTC-to-local conversion should be applied.
 * @return {string}                       The display-formatted string.
 */
const displayFormat = (dateString: stringOptional, outFormat: string, skipTimezone = false): string => {
    const possibleInputFormats = [
        serverDatetimeFormat,
        serverDateFormat,
    ];
    let display = '';

    if (dateString) {
        if (skipTimezone) {
            display = moment(dateString, possibleInputFormats).format(outFormat);
        } else {
            display = moment.utc(dateString, possibleInputFormats).local().format(outFormat);
        }
    }

    return display;
};

/**
 * Convert server datetime / date to date display format.
 * @param  {string} dateString The server date / datetime string.
 * @return {string}            The date display-formatted string.
 */
const dateDisplay = (dateString: stringOptional): string => displayFormat(dateString, displayDateFormat, true);

/**
 * Convert server datetime / date to datetime display format.
 * @param  {string} dateString The server date / datetime string.
 * @return {string}            The datetime display-formatted string.
 */
const datetimeDisplay = (dateString: stringOptional): string => displayFormat(dateString, displayDatetimeFormat);

/**
 * Convert server datetime / date to relative display format.
 * @param  {string}  dateString           The server date / datetime string.
 * @param  {boolean} [skipTimezone=false] TRUE if no UTC-to-local conversion should be applied.
 * @return {string}                       The datetime display-formatted string.
 */
const relativeFromNowDisplay = (dateString: stringOptional, skipTimezone = false): string => {
    const possibleInputFormats = [
        serverDatetimeFormat,
        serverDateFormat,
    ];
    let display = '';

    if (dateString) {
        if (skipTimezone) {
            display = moment(dateString, possibleInputFormats).fromNow(true);
        } else {
            display = moment.utc(dateString, possibleInputFormats).local().fromNow(true);
        }
    }

    return display;
};

/**
 * Get the unit diff between 2 dates using moment.
 * @param  {string}     date1                The first date string in server format.
 * @param  {string}     date2                The second date string in server format.
 * @param  {unitOfTime} [diffUnit='seconds'] Optional diff result units.
 * @return {number}                          The number of diff units.
 */
const dateDiff = (date1: stringOptional, date2: stringOptional, diffUnit: unitOfTime.Diff = 'seconds'): number => {
    const possibleInputFormats = [
        serverDatetimeFormat,
        serverDateFormat,
    ];
    const date1Moment: Moment = moment(date1, possibleInputFormats);
    const date2Moment: Moment = moment(date2, possibleInputFormats);
    let diff = 0;

    if (moment.isMoment(date1Moment) && moment.isMoment(date2Moment)) {
        diff = date1Moment.diff(date2Moment, diffUnit, true);
    }

    return diff;
};

/**
 * Format numeric date input (MMddyyyy) to MM/dd/yyyy display format
 * @param {string} value Raw numeric input (e.g., "12252024")
 * @return {string} Formatted date string (e.g., "12/25/2024")
 */
const formatDateInput = (value: string): string => {
    // Remove all non-numeric characters
    const numericOnly = (value || '').replace(/\D/g, '').substring(0, 8);

    // Apply MM/dd/yyyy formatting
    let formatted = numericOnly;

    if (numericOnly.length >= 2) {
        formatted = `${numericOnly.substring(0, 2)}/${numericOnly.substring(2)}`;
    }
    if (numericOnly.length >= 4) {
        formatted = `${numericOnly.substring(0, 2)}/${numericOnly.substring(2, 4)}/${numericOnly.substring(4, 8)}`;
    }

    return formatted;
};

/**
 * Convert numeric date input (MMddyyyy) to server format (yyyy-MM-dd)
 * @param {string} value Raw numeric input (e.g., "12252024")
 * @return {string} Server format date string (e.g., "2024-12-25") or empty string if invalid
 */
const dateInputToServerFormat = (value: string): string => {
    const numericOnly = (value || '').replace(/\D/g, '');
    let serverFormat = '';

    if (numericOnly.length === 8) {
        const month = numericOnly.substring(0, 2);
        const day = numericOnly.substring(2, 4);
        const year = numericOnly.substring(4, 8);
        const testDate = moment(`${year}-${month}-${day}`, 'YYYY-MM-DD', true);

        if (testDate.isValid()) {
            serverFormat = `${year}-${month}-${day}`;
        }
    }

    return serverFormat;
};

/**
 * Convert server format date (yyyy-MM-dd) to numeric input format (MMddyyyy)
 * @param {string} value Server format date string (e.g., "2024-12-25")
 * @return {string} Numeric format (e.g., "12252024")
 */
const serverFormatToDateInput = (value: string): string => {
    let dateInput = '';
    const isDateValid = moment(value, 'YYYY-MM-DD', true);

    if (value && isDateValid) {
        const dateParts = value.split('-');

        if (dateParts.length === 3) {
            const [year, month, day] = dateParts;

            dateInput = `${month}${day}${year}`;
        }
    }

    return dateInput;
};

/**
 * Validate if numeric date input represents a valid date
 * @param {string} value Raw numeric input (e.g., "12252024")
 * @return {boolean} True if valid date
 */
const isValidDateInput = (value: string): boolean => {
    const serverFormat = dateInputToServerFormat(value);
    let isValid = false;

    if (serverFormat) {
        // Try to create a valid date from the formatted input
        const date = new Date(serverFormat);
        const isValidDate = date instanceof Date && !Number.isNaN(date.getTime());

        if (isValidDate) {
            // Additional validation: check if the date components match what was input
            const [year, month, day] = serverFormat.split('-').map((num) => parseInt(num, 10));

            isValid = date.getFullYear() === year
                && date.getMonth() + 1 === month
                && date.getDate() === day;
        }
    }

    return isValid;
};

export {
    dateDisplay,
    datetimeDisplay,
    relativeFromNowDisplay,
    dateDiff,
    formatDateInput,
    dateInputToServerFormat,
    serverFormatToDateInput,
    isValidDateInput
};
