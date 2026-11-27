//
//  ApplicationConfig.model.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 11/17/2026.
//

import chaiMatchPattern from 'chai-match-pattern';
import { use, expect } from 'chai';
import { ApplicationConfig, ApplicationConfigSerializer } from '@models/ApplicationConfig/ApplicationConfig.model';
import { ApplicationType } from '@models/Application/Application.model';

use(chaiMatchPattern);

describe('ApplicationConfig model', () => {
    it('should create an ApplicationConfig with expected defaults', () => {
        const applicationConfig = new ApplicationConfig();

        // Test field values
        expect(applicationConfig).to.be.an.instanceof(ApplicationConfig);
        expect(applicationConfig.compactType).to.equal(null);
        expect(applicationConfig.fees).to.matchPattern({});

        // Test methods
        expect(applicationConfig.feeForType(ApplicationType.APIT)).to.equal(0);
        expect(applicationConfig.feeForType(ApplicationType.TAP)).to.equal(0);
        expect(applicationConfig.totalFeeForTypes([])).to.equal(0);
        expect(applicationConfig.totalFeeForTypes([ApplicationType.APIT, ApplicationType.TAP])).to.equal(0);
    });
    it('should create an ApplicationConfig with specific values', () => {
        const data = {
            compactType: 'psypact',
            fees: {
                [ApplicationType.APIT]: 100,
                [ApplicationType.TAP]: 50,
            },
        };
        const applicationConfig = new ApplicationConfig(data);

        // Test field values
        expect(applicationConfig).to.be.an.instanceof(ApplicationConfig);
        expect(applicationConfig.compactType).to.equal(data.compactType);
        expect(applicationConfig.fees).to.matchPattern(data.fees);

        // Test methods
        expect(applicationConfig.feeForType(ApplicationType.APIT)).to.equal(100);
        expect(applicationConfig.feeForType(ApplicationType.TAP)).to.equal(50);
        expect(applicationConfig.totalFeeForTypes([])).to.equal(0);
        expect(applicationConfig.totalFeeForTypes([ApplicationType.APIT])).to.equal(100);
        expect(applicationConfig.totalFeeForTypes([ApplicationType.TAP])).to.equal(50);
        expect(applicationConfig.totalFeeForTypes([ApplicationType.APIT, ApplicationType.TAP])).to.equal(150);
    });
    it('should create an ApplicationConfig with specific values through serializer', () => {
        const data = {
            compact: 'psypact',
            applicationFees: [
                { applicationType: 'apit', amount: 100 },
                { applicationType: 'tap', amount: '50' },
            ],
        };
        const applicationConfig = ApplicationConfigSerializer.fromServer(data);

        // Test field values
        expect(applicationConfig).to.be.an.instanceof(ApplicationConfig);
        expect(applicationConfig.compactType).to.equal(data.compact);
        expect(applicationConfig.fees).to.matchPattern({
            [ApplicationType.APIT]: 100,
            [ApplicationType.TAP]: 50,
        });

        // Test methods
        expect(applicationConfig.totalFeeForTypes([ApplicationType.APIT, ApplicationType.TAP])).to.equal(150);
    });
    it('should create an ApplicationConfig with fallback values through serializer', () => {
        const applicationConfig = ApplicationConfigSerializer.fromServer({
            applicationFees: [
                { applicationType: 'apit', amount: 'not-a-number' },
            ],
        });
        const emptyApplicationConfig = ApplicationConfigSerializer.fromServer(null);

        // Test field values
        expect(applicationConfig.compactType).to.equal(null);
        expect(applicationConfig.fees).to.matchPattern({ [ApplicationType.APIT]: 0 });
        expect(emptyApplicationConfig.compactType).to.equal(null);
        expect(emptyApplicationConfig.fees).to.matchPattern({});
    });
    it('should fall back when fees are undefined', () => {
        const applicationConfig = new ApplicationConfig();

        applicationConfig.fees = undefined;

        // Test methods
        expect(applicationConfig.feeForType(ApplicationType.APIT)).to.equal(0);
        expect(applicationConfig.totalFeeForTypes([ApplicationType.APIT, ApplicationType.TAP])).to.equal(0);
    });
});
