//
//  currency.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 5/15/25.
//

/**
 * Currency formatter for active input.
 * @param  {string | number} value The active input value.
 * @return {string}
 */
const formatCurrencyInput = (value: string | number = ''): string => {
    let [ dollars, cents ] = value.toString().split(/\.(.*)/s);
    const hasDecimal = cents !== undefined;
    let formatted = '';

    // Get raw dollar & cent values
    dollars = dollars.replace(/\D/g, '');
    cents = (hasDecimal) ? cents.replace(/\D/g, '') : '';

    // Prevent cents from having too many decimal places
    if (cents.length > 2) {
        cents = cents.slice(0, 2);
    }

    // Format with more forgiving typing-in-progress allowances
    if (dollars && hasDecimal) {
        formatted = `${dollars}.${cents}`;
    } else if (dollars) {
        formatted = `${dollars}`;
    } else if (cents) {
        formatted = `0.${cents}`;
    }

    return formatted;
};

/**
 * Currency formatter for completed input.
 * @param  {string | number} value              The active input value.
 * @param  {boolean}         [isOptional=false] TRUE if the input value is optional.
 * @return {string}
 */
const formatCurrencyBlur = (value: string | number = '', isOptional = false): string => {
    let [ dollars, cents ] = value.toString().split(/\.(.*)/s);
    let formatted = '';

    if (!value && isOptional) {
        // Autofill if optional input is blank
        dollars = '0';
    } else if (cents?.length === 1) {
        // Add trailing digit to cents if needed
        cents += '0';
    } else if (cents?.length > 2) {
        // Prevent cents from having too many decimal places
        cents = cents.slice(0, 2);
    }

    // Format with more strict done-typing cleanups
    if (dollars && cents) {
        formatted = `${dollars}.${cents}`;
    } else if (dollars) {
        formatted = `${dollars}`;
    } else if (cents) {
        formatted = `0.${cents}`;
    }

    return formatted;
};

export {
    formatCurrencyInput,
    formatCurrencyBlur,
};
