//
//  sorting.spec.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 6/12/24.
//

import mutations, { MutationTypes } from './sorting.mutations';

const chaiMatchPattern = require('chai-match-pattern');
const chai = require('chai').use(chaiMatchPattern);

const { expect } = chai;

describe('Sorting Store Mutations', () => {
    it('should successfully update sorting direction (id does not exist in store)', () => {
        const state = { sortingMap: {}};
        const sortingId = '1';
        const newDirection = 'asc';

        mutations[MutationTypes.UPDATE_SORTING_DIRECTION](state, { sortingId, newDirection });

        expect(state.sortingMap[sortingId]).to.matchPattern({ direction: newDirection });
    });
    it('should successfully update sorting direction (id exists in store)', () => {
        const state = { sortingMap: { '1': { direction: 'desc' }}};
        const sortingId = '1';
        const newDirection = 'asc';

        mutations[MutationTypes.UPDATE_SORTING_DIRECTION](state, { sortingId, newDirection });

        expect(state.sortingMap[sortingId]).to.matchPattern({ direction: newDirection });
    });
    it('should successfully update sorting option (id does not exist in store)', () => {
        const state = { sortingMap: {}};
        const sortingId = '1';
        const newOption = 'name';

        mutations[MutationTypes.UPDATE_SORTING_OPTION](state, { sortingId, newOption });

        expect(state.sortingMap[sortingId]).to.matchPattern({ option: newOption });
    });
    it('should successfully update sorting option (id exists in store)', () => {
        const state = { sortingMap: { '1': { option: 'address' }}};
        const sortingId = '1';
        const newOption = 'name';

        mutations[MutationTypes.UPDATE_SORTING_OPTION](state, { sortingId, newOption });

        expect(state.sortingMap[sortingId]).to.matchPattern({ option: newOption });
    });
    it('should successfully reset sorting', () => {
        const state = { sortingMap: {}};

        mutations[MutationTypes.RESET_SORTING](state);

        expect(state).to.matchPattern(state);
    });
});
