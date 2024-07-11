//
//  State.model.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 7/8/2024.
//

import { expect } from 'chai';
import { State, StateSerializer } from '@models/State/State.model';
import i18n from '@/i18n';

describe('State model', () => {
    before(() => {
        const { tm: $tm } = i18n.global;

        (window as any).Vue = {
            config: {
                globalProperties: {
                    $tm,
                }
            }
        };
    });
    it('should create a State with default values', () => {
        const state = new State();

        // Test field values
        expect(state).to.be.an.instanceof(State);
        expect(state.id).to.equal(null);
        expect(state.abbrev).to.equal(null);

        // Test methods
        expect(state.name()).to.equal('');
    });
    it('should create a State with specific values', () => {
        const data = {
            id: 'test-id',
            abbrev: 'test-abbrev',
        };
        const state = new State(data);

        // Test field values
        expect(state).to.be.an.instanceof(State);
        expect(state.id).to.equal(data.id);
        expect(state.abbrev).to.equal(data.abbrev);

        // Test methods
        expect(state.name()).to.equal('');
    });
    it('should create a State with specific values through serializer', () => {
        const data = {
            id: 'test-id',
            abbrev: 'co',
        };
        const state = StateSerializer.fromServer(data);

        // Test field values
        expect(state).to.be.an.instanceof(State);
        expect(state.id).to.equal(data.id);
        expect(state.abbrev).to.equal(data.abbrev);

        // Test methods
        expect(state.name()).to.equal('Colorado');
    });
    it('should serialize a State with for transmission to the server', () => {
        const state = StateSerializer.fromServer({
            id: 'test-id',
            abbrev: 'co',
        });
        const transmit = StateSerializer.toServer(state);

        expect(transmit.id).to.equal(state.id);
        expect(transmit.abbrev).to.equal(state.abbrev);
    });
});
