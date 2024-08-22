//
//  session.storage.spec.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 4/12/20.
//

import store from './index';

const chaiMatchPattern = require('chai-match-pattern');
const chai = require('chai').use(chaiMatchPattern);

const { expect } = chai;

describe('Session Storage store', () => {
    it('should successfully check if sessionStorage is available (available)', () => {
        const isAvailable = store.isSessionStorageAvailable();

        expect(isAvailable).to.equal(true);
    });
    it('should successfully set sessionStorage item', () => {
        const key = 'testKey1';
        const value = 'testValue';
        const result = store.setItem(key, value);

        expect(result).to.equal(value);
    });
    it('should successfully set sessionStorage JSON item', () => {
        const key = 'testKey2';
        const value = { test: 'testValue' };
        const result = store.setItemJson(key, value);

        expect(result).to.equal(JSON.stringify(value));
    });
    it('should successfully get sessionStorage item', () => {
        const key = 'testKey1';
        const result = store.getItem(key);

        expect(result).to.equal('testValue');
    });
    it('should successfully get sessionStorage JSON item', () => {
        const key = 'testKey2';
        const result = store.getItemJson(key);

        expect(result).to.matchPattern({ test: 'testValue' });
    });
    it('should successfully remove sessionStorage item', () => {
        const key = 'testKey2';
        const result = store.removeItem(key);

        expect(result).to.equal(true);
        expect(store.getItem(key)).to.equal(null);
    });
});
