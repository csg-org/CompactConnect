//
//  PrivilegePurchaseOption.model.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 7/8/2024.
//

import { expect } from 'chai';
import { FeeTypes } from '@/app.config';
import {
    PrivilegePurchaseOption,
    PrivilegePurchaseOptionSerializer
} from '@models/PrivilegePurchaseOption/PrivilegePurchaseOption.model';
import { State } from '@models/State/State.model';
import i18n from '@/i18n';

describe('PrivilegePurchaseOption model', () => {
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
    it('should create a PrivilegePurchaseOption with expected defaults', () => {
        const privilegePurchaseOption = new PrivilegePurchaseOption();

        // Test field values
        expect(privilegePurchaseOption).to.be.an.instanceof(PrivilegePurchaseOption);
        expect(privilegePurchaseOption.jurisdiction).to.be.an.instanceof(State);
        expect(privilegePurchaseOption.compact).to.equal(null);
        expect(privilegePurchaseOption.fee).to.equal(null);
        expect(privilegePurchaseOption.isMilitaryDiscountActive).to.equal(false);
        expect(privilegePurchaseOption.militaryDiscountType).to.equal(null);
        expect(privilegePurchaseOption.militaryDiscountAmount).to.equal(null);
        expect(privilegePurchaseOption.isJurisprudenceRequired).to.equal(false);
    });
    it('should create a PrivilegePurchaseOption with specific values', () => {
        const data = {
            jurisdiction: new State({ abbrev: 'ca' }),
            compact: 'aslp',
            fee: 5,
            isMilitaryDiscountActive: true,
            militaryDiscountType: FeeTypes.FLAT_RATE,
            militaryDiscountAmount: 10,
            isJurisprudenceRequired: true,
        };
        const privilegePurchaseOption = new PrivilegePurchaseOption(data);

        expect(privilegePurchaseOption).to.be.an.instanceof(PrivilegePurchaseOption);
        expect(privilegePurchaseOption.jurisdiction).to.be.an.instanceof(State);
        expect(privilegePurchaseOption.jurisdiction.abbrev).to.equal('ca');
        expect(privilegePurchaseOption.compact).to.equal(data.compact);
        expect(privilegePurchaseOption.fee).to.equal(5);
        expect(privilegePurchaseOption.isMilitaryDiscountActive).to.equal(true);
        expect(privilegePurchaseOption.militaryDiscountType).to.equal(FeeTypes.FLAT_RATE);
        expect(privilegePurchaseOption.militaryDiscountAmount).to.equal(10);
        expect(privilegePurchaseOption.isJurisprudenceRequired).to.equal(true);
    });
    it('should create a PrivilegePurchaseOption with specific values through serializer', () => {
        const data = {
            jurisdictionName: 'kentucky',
            postalAbbreviation: 'ky',
            compact: 'aslp',
            jurisdictionFee: 100,
            militaryDiscount: {
                active: true,
                discountType: 'FLAT_RATE',
                discountAmount: 10
            },
            jurisprudenceRequirements: {
                required: true
            },
            type: 'jurisdiction'
        };

        const privilegePurchaseOption = PrivilegePurchaseOptionSerializer.fromServer(data);

        // Test field values
        expect(privilegePurchaseOption).to.be.an.instanceof(PrivilegePurchaseOption);
        expect(privilegePurchaseOption.jurisdiction).to.be.an.instanceof(State);
        expect(privilegePurchaseOption.jurisdiction.abbrev).to.equal('ky');
        expect(privilegePurchaseOption.compact).to.equal('aslp');
        expect(privilegePurchaseOption.fee).to.equal(100);
        expect(privilegePurchaseOption.isMilitaryDiscountActive).to.equal(true);
        expect(privilegePurchaseOption.militaryDiscountType).to.equal(FeeTypes.FLAT_RATE);
        expect(privilegePurchaseOption.militaryDiscountAmount).to.equal(10);
        expect(privilegePurchaseOption.isJurisprudenceRequired).to.equal(true);
    });
    it('should create a PrivilegePurchaseOption with specific values and null military discount object through serializer', () => {
        const data = {
            jurisdictionName: 'kentucky',
            postalAbbreviation: 'ky',
            compact: 'aslp',
            jurisdictionFee: 100,
            militaryDiscount: null,
            jurisprudenceRequirements: {
                required: true
            },
            type: 'jurisdiction'
        };

        const privilegePurchaseOption = PrivilegePurchaseOptionSerializer.fromServer(data);

        // Test field values
        expect(privilegePurchaseOption).to.be.an.instanceof(PrivilegePurchaseOption);
        expect(privilegePurchaseOption.jurisdiction).to.be.an.instanceof(State);
        expect(privilegePurchaseOption.jurisdiction.abbrev).to.equal('ky');
        expect(privilegePurchaseOption.compact).to.equal('aslp');
        expect(privilegePurchaseOption.fee).to.equal(100);
        expect(privilegePurchaseOption.isMilitaryDiscountActive).to.equal(false);
        expect(privilegePurchaseOption.militaryDiscountType).to.equal(null);
        expect(privilegePurchaseOption.militaryDiscountAmount).to.equal(null);
        expect(privilegePurchaseOption.isJurisprudenceRequired).to.equal(true);
    });
});
