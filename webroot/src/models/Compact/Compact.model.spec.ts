//
//  Compact.model.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 8/27/2024.
//

import { compacts as compactConfigs, FeeTypes } from '@/app.config';
import { expect } from 'chai';
import { Compact, CompactSerializer, CompactType } from '@models/Compact/Compact.model';
import { PrivilegePurchaseOption } from '@models/PrivilegePurchaseOption/PrivilegePurchaseOption.model';
import { State } from '@models/State/State.model';
import i18n from '@/i18n';

describe('Compact model', () => {
    before(() => {
        const { tm: $tm } = i18n.global;

        (window as any).Vue = {
            config: {
                globalProperties: {
                    $tm,
                }
            }
        };
        i18n.global.locale = 'en';
    });
    it('should create a Compact with default values', () => {
        const compact = new Compact();

        // Test field values
        expect(compact).to.be.an.instanceof(Compact);
        expect(compact.id).to.equal(null);
        expect(compact.type).to.equal(null);
        expect(compact.privilegePurchaseOptions).to.be.an('array').that.is.empty;
        expect(compact.compactCommissionFee).to.equal(null);
        expect(compact.compactCommissionFeeType).to.equal(null);
        expect(compact.memberStates).to.be.an('array').that.is.empty;

        // Test methods
        expect(compact.name()).to.equal('');
        expect(compact.abbrev()).to.equal('');
    });
    it('should create a Compact with specific values', () => {
        const data = {
            id: 'test-id',
            type: CompactType.ASLP,
            memberStates: [new State()],
            privilegePurchaseOptions: [new PrivilegePurchaseOption()],
            compactCommissionFee: 10,
            compactCommissionFeeType: FeeTypes.FLAT_RATE

        };
        const compact = new Compact(data);

        // Test field values
        expect(compact).to.be.an.instanceof(Compact);
        expect(compact.id).to.equal(data.id);
        expect(compact.type).to.equal(data.type);
        expect(compact.memberStates).to.be.an('array').with.length(1);
        expect(compact.memberStates[0]).to.be.an.instanceof(State);
        expect(compact.privilegePurchaseOptions).to.be.an('array').with.length(1);
        expect(compact.privilegePurchaseOptions[0]).to.be.an.instanceof(PrivilegePurchaseOption);
        expect(compact.compactCommissionFee).to.equal(data.compactCommissionFee);
        expect(compact.compactCommissionFeeType).to.equal(data.compactCommissionFeeType);

        // Test methods
        expect(compact.name()).to.equal('Audio and Speech Language Pathology');
        expect(compact.abbrev()).to.equal('ASLP');
    });
    it('should create a Compact with specific values through serializer', () => {
        const data = {
            id: 'test-id',
            type: CompactType.ASLP,
        };
        const compact = CompactSerializer.fromServer(data);
        const compactStates = compactConfigs[CompactType.ASLP].memberStates;

        // Test field values
        expect(compact).to.be.an.instanceof(Compact);
        expect(compact.id).to.equal(data.id);
        expect(compact.type).to.equal(data.type);
        expect(compact.memberStates).to.be.an('array').with.length(33);

        compact.memberStates.forEach((state, idx) => {
            expect(state).to.be.an.instanceof(State);
            expect(state.abbrev).to.equal(compactStates[idx]);
        });

        // Test methods
        expect(compact.name()).to.equal('Audio and Speech Language Pathology');
        expect(compact.abbrev()).to.equal('ASLP');
    });
});
