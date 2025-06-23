//
//  formatters.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 7/20/2024.
//

import { expect } from 'chai';
import {
    serverDatetimeFormat,
    serverDateFormat,
    displayDateFormat,
    displayDatetimeFormat
} from '@/app.config';
import {
    dateDisplay,
    datetimeDisplay,
    relativeFromNowDisplay,
    dateDiff,
    formatDateInput,
    dateInputToServerFormat,
    serverFormatToDateInput
} from '@models/_formatters/date';
import { singleDelimeterPhoneFormatter, formatPhoneNumber, stripPhoneNumber } from '@models/_formatters/phone';
import { formatCurrencyInput, formatCurrencyBlur } from '@models/_formatters/currency';
import moment from 'moment';

describe('Date formatters', () => {
    it('should display a server date in the expected format with no timezone conversion', () => {
        const serverMoment = moment.utc();
        const serverDate = serverMoment.format(serverDateFormat);
        const displayDate = dateDisplay(serverDate);
        const displayMoment = moment(displayDate, displayDateFormat);

        expect(moment.isMoment(serverMoment)).to.equal(true);
        expect(moment.isMoment(displayMoment)).to.equal(true);
        expect(displayMoment.diff(serverMoment, 'days')).to.equal(0);
    });
    it('should display a server datetime in the expected format with local timezone conversion', () => {
        const serverMoment = moment.utc();
        const serverDatetime = serverMoment.format(serverDatetimeFormat);
        const displayDatetime = datetimeDisplay(serverDatetime);
        const displayMoment = moment(displayDatetime, displayDatetimeFormat);

        expect(moment.isMoment(displayMoment)).to.equal(true);
    });
    it('should display a server date in the expected format with local timezone conversion', () => {
        const serverMoment = moment();
        const serverDate = serverMoment.format(serverDateFormat);
        const displayDate = relativeFromNowDisplay(serverDate);

        expect(displayDate).to.be.a('string').that.is.not.empty;
    });
    it('should calculate a date diff in the default unit', () => {
        const date1 = moment();
        const date2 = moment().subtract(5, 'seconds');
        const diff = Math.round(dateDiff(date1, date2));

        expect(diff).to.equal(5);
    });
    it('should calculate a date diff in days', () => {
        const date1 = moment();
        const date2 = moment().subtract(5, 'days');
        const diff = Math.round(dateDiff(date1, date2, 'days'));

        expect(diff).to.equal(5);
    });
    it('should format raw date input to MM/dd/yyyy display format', () => {
        const formatted = formatDateInput('12252024');

        expect(formatted).to.equal('12/25/2024');
    });
    it('should format partial date input correctly', () => {
        const formatted1 = formatDateInput('12');
        const formatted2 = formatDateInput('1225');
        const formatted3 = formatDateInput('122520');

        expect(formatted1).to.equal('12/');
        expect(formatted2).to.equal('12/25/');
        expect(formatted3).to.equal('12/25/20');
    });
    it('should format already formatted date input', () => {
        const formatted = formatDateInput('12/25/2024');

        expect(formatted).to.equal('12/25/2024');
    });
    it('should handle empty input for formatDateInput', () => {
        const formatted = formatDateInput('');

        expect(formatted).to.equal('');
    });
    it('should strip non-numeric characters from date input', () => {
        const formatted = formatDateInput('12a25b2024c');

        expect(formatted).to.equal('12/25/2024');
    });
    it('should convert valid date input to server format', () => {
        const serverFormat = dateInputToServerFormat('12252024');

        expect(serverFormat).to.equal('2024-12-25');
    });
    it('should convert formatted date input to server format', () => {
        const serverFormat = dateInputToServerFormat('12/25/2024');

        expect(serverFormat).to.equal('2024-12-25');
    });
    it('should return empty string for invalid date input to server format', () => {
        const serverFormat1 = dateInputToServerFormat('13252024'); // Invalid month
        const serverFormat2 = dateInputToServerFormat('12322024'); // Invalid day
        const serverFormat3 = dateInputToServerFormat('1225'); // Incomplete date

        expect(serverFormat1).to.equal('');
        expect(serverFormat2).to.equal('');
        expect(serverFormat3).to.equal('');
    });
    it('should handle empty input for dateInputToServerFormat', () => {
        const serverFormat = dateInputToServerFormat('');

        expect(serverFormat).to.equal('');
    });
    it('should convert server format date to numeric input format', () => {
        const dateInput = serverFormatToDateInput('2024-12-25');

        expect(dateInput).to.equal('12252024');
    });
    it('should handle invalid server format date', () => {
        const dateInput1 = serverFormatToDateInput('2024-13-25'); // Invalid month
        const dateInput2 = serverFormatToDateInput('invalid-date');
        const dateInput3 = serverFormatToDateInput('2024/12/25'); // Wrong format

        expect(dateInput1).to.equal('');
        expect(dateInput2).to.equal('');
        expect(dateInput3).to.equal('');
    });
    it('should handle empty input for serverFormatToDateInput', () => {
        const dateInput = serverFormatToDateInput('');

        expect(dateInput).to.equal('');
    });
});
describe('Phone formatters', () => {
    it('should return empty string when formatting no input phone number', () => {
        const formatted = singleDelimeterPhoneFormatter();

        expect(formatted).to.equal('');
    });
    it('should return empty string when stripping no input phone number', () => {
        const stripped = stripPhoneNumber();

        expect(stripped).to.equal('');
    });
    it('should return intelligently formatted phone number with lengths between 3 and 10 digits', () => {
        const formatted = formatPhoneNumber('1234');

        expect(formatted).to.equal('123-4');
    });
    it('should return intelligently formatted phone number with lengths less than 3', () => {
        const formatted = formatPhoneNumber('12');

        expect(formatted).to.equal('12');
    });
});
describe('Currency formatters', () => {
    it('should return empty when value param is empty (input)', () => {
        const formatted = formatCurrencyInput();

        expect(formatted).to.equal('');
    });
    it('should return correctly formatted when value param is only dollars (input)', () => {
        const formatted = formatCurrencyInput('10');

        expect(formatted).to.equal('10');
    });
    it('should return correctly formatted when value param is only dollars with trailing decimal point (input)', () => {
        const formatted = formatCurrencyInput('10.');

        expect(formatted).to.equal('10.');
    });
    it('should return correctly formatted when value param has partial cents (input)', () => {
        const formatted = formatCurrencyInput('1.1');

        expect(formatted).to.equal('1.1');
    });
    it('should return correctly formatted when value param has too much precision for cents (input)', () => {
        const formatted = formatCurrencyInput('1.111');

        expect(formatted).to.equal('1.11');
    });
    it('should return correctly formatted when value param cents only (input)', () => {
        const formatted = formatCurrencyInput('.111');

        expect(formatted).to.equal('0.11');
    });
    it('should return empty for blur when value param is empty (blur)', () => {
        const formatted = formatCurrencyBlur();

        expect(formatted).to.equal('');
    });
    it('should return return correctly formatted when value param is empty and discretely not optional (blur)', () => {
        const formatted = formatCurrencyBlur('', false);

        expect(formatted).to.equal('');
    });
    it('should return return correctly formatted when value param is empty and optional (blur)', () => {
        const formatted = formatCurrencyBlur('', true);

        expect(formatted).to.equal('0');
    });
    it('should return return correctly formatted when value param only has 1 decimal place for cents (blur)', () => {
        const formatted = formatCurrencyBlur('1.1');

        expect(formatted).to.equal('1.10');
    });
    it('should return correctly formatted when value param is only dollars (blur)', () => {
        const formatted = formatCurrencyBlur('1');

        expect(formatted).to.equal('1');
    });
    it('should return correctly formatted when value param is only dollars with trailing decimal point (blur)', () => {
        const formatted = formatCurrencyBlur('1.');

        expect(formatted).to.equal('1');
    });
    it('should return correctly formatted when value param cents only (blur)', () => {
        const formatted = formatCurrencyBlur('.111');

        expect(formatted).to.equal('0.11');
    });
});
