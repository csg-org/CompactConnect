//
//  CompactFeeConfig.model.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 2/17/2025.
//

import { expect } from 'chai';
import { FeeTypes } from '@/app.config';
import { CompactFeeConfig, CompactFeeConfigSerializer } from '@models/CompactFeeConfig/CompactFeeConfig.model';

describe('CompactFeeConfig model', () => {
    it('should create a CompactFeeConfig with default values', () => {
        const compactFeeConfiguration = new CompactFeeConfig();

        // Test field values
        expect(compactFeeConfiguration).to.be.an.instanceof(CompactFeeConfig);
        expect(compactFeeConfiguration.compactType).to.equal('');
        expect(compactFeeConfiguration.compactCommissionFee).to.equal(0);
        expect(compactFeeConfiguration.compactCommissionFeeType).to.equal(null);
        expect(compactFeeConfiguration.perPrivilegeTransactionFeeAmount).to.equal(0);
        expect(compactFeeConfiguration.isPerPrivilegeTransactionFeeActive).to.equal(false);
    });
    it('should create a CompactFeeConfig with specific values', () => {
        const data = {
            compactType: 'aslp',
            compactCommissionFee: 10,
            compactCommissionFeeType: FeeTypes.FLAT_RATE,
            perPrivilegeTransactionFeeAmount: 3,
            isPerPrivilegeTransactionFeeActive: true,

        };
        const compactFeeConfiguration = new CompactFeeConfig(data);

        // Test field values
        expect(compactFeeConfiguration).to.be.an.instanceof(CompactFeeConfig);
        expect(compactFeeConfiguration.compactType).to.equal('aslp');
        expect(compactFeeConfiguration.compactCommissionFee).to.equal(10);
        expect(compactFeeConfiguration.compactCommissionFeeType).to.equal(FeeTypes.FLAT_RATE);
        expect(compactFeeConfiguration.perPrivilegeTransactionFeeAmount).to.equal(3);
        expect(compactFeeConfiguration.isPerPrivilegeTransactionFeeActive).to.equal(true);
    });
    it('should create a CompactFeeConfig with specific values through serializer', () => {
        const data = {
            compactAbbr: 'aslp',
            compactCommissionFee: {
                feeType: 'FLAT_RATE',
                feeAmount: 3.5
            },
            transactionFeeConfiguration: {
                licenseeCharges: {
                    active: true,
                    chargeType: 'FLAT_FEE_PER_PRIVILEGE',
                    chargeAmount: 2
                }
            },
            type: 'compact'
        };
        const compactFeeConfiguration = CompactFeeConfigSerializer.fromServer(data);

        // Test field values
        expect(compactFeeConfiguration).to.be.an.instanceof(CompactFeeConfig);
        expect(compactFeeConfiguration.compactType).to.equal('aslp');
        expect(compactFeeConfiguration.compactCommissionFee).to.equal(3.5);
        expect(compactFeeConfiguration.compactCommissionFeeType).to.equal(FeeTypes.FLAT_RATE);
        expect(compactFeeConfiguration.perPrivilegeTransactionFeeAmount).to.equal(2);
        expect(compactFeeConfiguration.isPerPrivilegeTransactionFeeActive).to.equal(true);
    });
});
