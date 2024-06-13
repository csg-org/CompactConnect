//
//  local.storage.spec.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 4/12/20.
//  Copyright © 2024. InspiringApps. All rights reserved.
//

import store from './index';

const chaiMatchPattern = require('chai-match-pattern');
const chai = require('chai').use(chaiMatchPattern);

const { expect } = chai;

describe('Local Storage store', () => {
    it('should successfully check if localStorage is available (available)', () => {
        const isAvailable = store.isLocalStorageAvailable();

        expect(isAvailable).to.equal(true);
    });
    it('should successfully set localStorage item', () => {
        const key = 'testKey1';
        const value = 'testValue';
        const result = store.setItem(key, value);

        expect(result).to.equal(value);
    });
    it('should successfully set localStorage JSON item', () => {
        const key = 'testKey2';
        const value = { test: 'testValue' };
        const result = store.setItemJson(key, value);

        expect(result).to.equal(JSON.stringify(value));
    });
    it('should successfully get localStorage item', () => {
        const key = 'testKey1';
        const result = store.getItem(key);

        expect(result).to.equal('testValue');
    });
    it('should successfully get localStorage JSON item', () => {
        const key = 'testKey2';
        const result = store.getItemJson(key);

        expect(result).to.matchPattern({ test: 'testValue' });
    });
    it('should successfully remove localStorage item', () => {
        const key = 'testKey2';
        const result = store.removeItem(key);

        expect(result).to.equal(true);
    });
});
