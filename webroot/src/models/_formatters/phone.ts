/**
 * Receive a string of numbers and return a NANP parentheses format phone number
 * @param {string} numberValue
 * @param {string} inputValue
 * @return {string} formattedPhoneNumber
 */
const parensPhoneFormatter = (numberValue: string, inputValue: string): string => {
    let formattedPhoneNumber = '';

    // If the number value is at least three digits
    if (numberValue.length >= 3) {
        // Allow the user to delete intuitively back through the NPA
        if (inputValue.length <= 4 && inputValue.indexOf('(') >= 0) {
            formattedPhoneNumber = numberValue;
        } else if ((inputValue.length === 5 || inputValue.length === 6) && inputValue.indexOf('(') >= 0) {
            formattedPhoneNumber = inputValue;
        } else {
            // otherwise add the NPA parens
            formattedPhoneNumber = `(${numberValue.substr(0, 3)}) `;
        }

        // If the number value is at least 7 digits
        if (numberValue.length >= 7) {
            // Add the NXX-Line dash
            formattedPhoneNumber += `${numberValue.substr(3, 3)}-${numberValue.substr(6, 4)}`;
        } else {
            // Otherwise just display the rest of the numbers unformatted
            formattedPhoneNumber += numberValue.substr(3);
        }
    } else {
        // Otherwise just display the numbers unformatted
        formattedPhoneNumber = numberValue;
    }

    return formattedPhoneNumber;
};

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
    if (numberValue.length >= 3) {
        // Add the post-NPA delimeter
        formattedPhoneNumber = numberValue.substring(0, 3) + delimeter;

        // If the number value is at least 6 digits
        if (numberValue.length >= 6) {
            // Add the post-NXX delimeter

            formattedPhoneNumber += numberValue.substring(3, 6) + delimeter + numberValue.substring(6, 10);
        } else {
            // Otherwise just display the rest of the numbers unformatted
            formattedPhoneNumber += numberValue.substring(3);
        }
    } else {
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
const formatPhoneNumber = (value: string, format: string): string => {
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

    // Set a formatted values based on the format type
    if (format === 'parens') {
        // (xxx) xxx-xxxx
        newValue = parensPhoneFormatter(numberValue, value);
    } else if (format === 'dashed') {
        // xxx-xxx-xxxx
        newValue = singleDelimeterPhoneFormatter(numberValue, '-');
    } else if (format === 'dotted') {
        // xxx.xxx.xxxx
        newValue = singleDelimeterPhoneFormatter(numberValue, '.');
    } else if (format === 'number') {
        // xxxxxxxxxx
        newValue = numberValue;
    } else {
        // No format assistance
        newValue = value;
        return newValue;
    }

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
    formatPhoneNumber,
    stripPhoneNumber,
};
