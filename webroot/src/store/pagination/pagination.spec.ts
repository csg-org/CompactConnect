//
//  pagination.spec.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 6/12/24.
//

import mutations, { MutationTypes } from './pagination.mutations';

const chaiMatchPattern = require('chai-match-pattern');
const chai = require('chai').use(chaiMatchPattern);

const { expect } = chai;
const defaultPageNum = 1;
const defaultPageSize = 25;

describe('Pagniation Store Mutations', () => {
    it('should successfully update pagination page (id does not exist in store)', () => {
        const state = { paginationMap: {}};
        const paginationId = '1';
        const newPage = 1;

        mutations[MutationTypes.UPDATE_PAGINATION_CURRENT_PAGE](state, { paginationId, newPage });

        expect(state.paginationMap[paginationId]).to.matchPattern({ page: newPage, size: defaultPageSize });
    });
    it('should successfully update pagination page (id exists in store)', () => {
        const state = { paginationMap: { '1': { page: 'desc' }}};
        const paginationId = '1';
        const newPage = 1;

        mutations[MutationTypes.UPDATE_PAGINATION_CURRENT_PAGE](state, { paginationId, newPage });

        expect(state.paginationMap[paginationId]).to.matchPattern({ page: newPage });
    });
    it('should successfully update pagination size (id does not exist in store)', () => {
        const state = { paginationMap: {}};
        const paginationId = '1';
        const newSize = 1;

        mutations[MutationTypes.UPDATE_PAGINATION_PAGE_SIZE](state, { paginationId, newSize });

        expect(state.paginationMap[paginationId]).to.matchPattern({ size: newSize, page: defaultPageNum });
    });
    it('should successfully update pagination size (id exists in store)', () => {
        const state = { paginationMap: { '1': { size: 'address' }}};
        const paginationId = '1';
        const newSize = 1;

        mutations[MutationTypes.UPDATE_PAGINATION_PAGE_SIZE](state, { paginationId, newSize });

        expect(state.paginationMap[paginationId]).to.matchPattern({ size: newSize });
    });
    it('should successfully reset pagination', () => {
        const state = { paginationMap: {}};

        mutations[MutationTypes.RESET_PAGINATION](state);

        expect(state).to.matchPattern(state);
    });
});
