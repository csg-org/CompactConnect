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
    dateDiff
} from '@models/_formatters/date';
import { singleDelimeterPhoneFormatter, formatPhoneNumber, stripPhoneNumber } from '@models/_formatters/phone';
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
