//
//  global.spec.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 4/12/20.
//  Copyright © 2024. InspiringApps. All rights reserved.
//

import mutations, { MutationTypes } from './global.mutations';

const chaiMatchPattern = require('chai-match-pattern');
const chai = require('chai').use(chaiMatchPattern);

const { expect } = chai;

describe('Global Store Mutations', () => {
    it('should successfully begin loading', () => {
        const state = {};

        mutations[MutationTypes.BEGIN_LOADING](state);

        expect(state.isLoading).to.equal(true);
        expect(state.error).to.equal(null);
    });
    it('should successfully end loading', () => {
        const state = {};

        mutations[MutationTypes.END_LOADING](state);

        expect(state.isLoading).to.equal(false);
    });
    it('should successfully set error', () => {
        const state = {};
        const error = new Error();

        mutations[MutationTypes.SET_ERROR](state, error);

        expect(state.error).to.equal(error);
    });
    it('should successfully push a message (no messages exist)', () => {
        const state = {};
        const message = 'message';

        mutations[MutationTypes.PUSH_MESSAGE](state, message);

        expect(state.messages).to.matchPattern([message]);
    });
    it('should successfully push a message (some messages exist)', () => {
        const state = { messages: [ 'existing' ]};
        const message = 'message';

        mutations[MutationTypes.PUSH_MESSAGE](state, message);

        expect(state.messages).to.matchPattern([ 'existing', message]);
    });
    it('should successfully clear messages', () => {
        const state = {};

        mutations[MutationTypes.CLEAR_MESSAGES](state);

        expect(state.messages).to.matchPattern([]);
    });
    it('should successfully reset store', () => {
        const state = {};

        mutations[MutationTypes.STORE_RESET_GLOBAL](state);

        expect(state).to.matchPattern({
            isLoading: false,
            error: null,
            messages: [],
            isModalOpen: false,
            isModalLogoutOnly: false,
        });
    });
    it('should successfully set modal open', () => {
        const state = {};
        const isModalOpen = true;

        mutations[MutationTypes.SET_MODAL_OPEN](state, isModalOpen);

        expect(state.isModalOpen).to.equal(isModalOpen);
    });
    it('should successfully set modal as logout-only', () => {
        const state = {};
        const isModalLogoutOnly = true;

        mutations[MutationTypes.SET_MODAL_LOGOUT_ONLY](state, isModalLogoutOnly);

        expect(state.isModalLogoutOnly).to.equal(isModalLogoutOnly);
    });
});
