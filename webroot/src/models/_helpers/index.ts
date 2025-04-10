import { dateDiff } from '@models/_formatters/date';
import moment from 'moment';

const deleteUndefinedProperties = (data = {}) => {
    const cleanObject = { ...data };

    Object.keys(cleanObject).forEach((key) => {
        if (`${key}` in cleanObject && cleanObject[key] === undefined) {
            delete cleanObject[key];
        }
    });

    return cleanObject;
};

const isDatePastExpiration = ({ date, dateOfExpiration }): boolean => {
    const dateOfRenewal = moment().format(date);
    const diff = dateDiff(dateOfRenewal, dateOfExpiration, 'days') || 0;

    return diff > 0;
};

export {
    deleteUndefinedProperties,
    isDatePastExpiration
};
