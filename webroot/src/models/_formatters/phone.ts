//
//  phone.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 4/12/20.
//

/**
 * Receive a string of numbers and return a delimeted phone number based
 * on the delimeter argument
 * @param {string} numberValue
 * @param {string} numberDelimeter
 * @return {string} formattedPhoneNumber
 */
const singleDelimeterPhoneFormatter = (numberValue: string, numberDelimeter: string): string => {
    let formattedPhoneNumber = '';
    const delimeter = numberDelimeter || '-';

    // If the number value is at least three digits
    if (numberValue?.length >= 3) {
        // Add the post-NPA delimeter
        formattedPhoneNumber = numberValue.substring(0, 3) + delimeter;

        // If the number value is at least 6 digits
        if (numberValue.length >= 6) {
            // Add the post-NXX delimeter

            formattedPhoneNumber += numberValue.substring(3, 6) + delimeter + numberValue.substring(6);
        } else {
            // Otherwise just display the rest of the numbers unformatted
            formattedPhoneNumber += numberValue.substring(3);
        }
    } else if (numberValue) {
        // Otherwise just display the numbers unformatted
        formattedPhoneNumber = numberValue;
    }

    return formattedPhoneNumber;
};

/**
 * Receive the phone number input text and format. Extract the
 * numeric phone number value to send to the appropriate formatter
 * @param {string} value
 * @param {string} format
 * @return {string} newValue
 */
const formatPhoneNumber = (value: string): string => {
    let valueLength = 0;
    let numberValue = '';
    let countryCode = '';
    let newValue = '';
    let character = '';
    let i = 0;
    const numberTest = new RegExp('[0-9]');

    // Get the length of the input string
    valueLength = value.length;

    // Extract the numbers from the input string
    for (i = 0; i < valueLength; i += 1) {
        character = value.charAt(i);
        if (numberTest.test(character)) {
            numberValue += character;
        }
    }

    // Extract country code
    if (numberValue.length > 10) {
        const allNumbers = numberValue.slice();

        numberValue = allNumbers.slice(-10);
        countryCode = allNumbers.slice(0, allNumbers.length - 10);
    }

    newValue = singleDelimeterPhoneFormatter(numberValue, '-');

    // Return the formatted phone number
    return (countryCode) ? `+${countryCode} ${newValue}` : newValue;
};

const stripPhoneNumber = (value: string): string => {
    if (!value) {
        return '';
    }

    return value.replace(/\D/g, '');
};

export {
    singleDelimeterPhoneFormatter,
    formatPhoneNumber,
    stripPhoneNumber,
};
