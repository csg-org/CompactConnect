//
//  mock.data.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 9/24/2026.
//

import { expect } from 'chai';
import { CompactType } from '@models/Compact/Compact.model';
import {
    licensees,
    mockProviderCompactOverlays,
    applyProviderCompactOverlay,
    getMockProviderForCompact
} from '@network/mocks/mock.data';

describe('mock provider compact overlays', () => {
    const sourceProvider = licensees.providers[0];

    const expectProviderOverlay = (compactType: CompactType) => {
        const sourceSnapshot = JSON.parse(JSON.stringify(sourceProvider));
        const overlay = mockProviderCompactOverlays[compactType];
        const provider = getMockProviderForCompact(sourceProvider, compactType);

        expect(provider).to.not.equal(sourceProvider);
        expect(provider.compact).to.equal(overlay.compact);
        expect(provider.licenseType).to.equal(overlay.licenseType);
        /* eslint-disable function-paren-newline */
        expect(provider.licenses.every((license) =>
            license.compact === overlay.compact
            && license.licenseType === overlay.licenseType
        )).to.equal(true);
        expect(provider.privileges.every((privilege) =>
            privilege.compact === overlay.compact
            && privilege.licenseType === overlay.licenseType
        )).to.equal(true);
        expect(provider.militaryAffiliations.every((affiliation) =>
            affiliation.compact === overlay.compact
            && affiliation.licenseType === undefined
        )).to.equal(true);
        /* eslint-enable function-paren-newline */
        expect(sourceProvider).to.deep.equal(sourceSnapshot);
    };

    it('should apply the ASLP overlay', () => {
        expectProviderOverlay(CompactType.ASLP);
    });
    it('should apply the OT overlay', () => {
        expectProviderOverlay(CompactType.OT);
    });
    it('should apply the counseling overlay', () => {
        expectProviderOverlay(CompactType.COUNSELING);
    });
    it('should apply the cosmetology overlay', () => {
        expectProviderOverlay(CompactType.COSMETOLOGY);
    });
    it('should apply the social work overlay', () => {
        expectProviderOverlay(CompactType.SOCIAL_WORK);
    });
    it('should apply the PSYPACT overlay', () => {
        expectProviderOverlay(CompactType.PSYPACT);
    });
    it('should apply the dietitians overlay', () => {
        expectProviderOverlay(CompactType.DIETITIANS);
    });
    it('should return the original provider when an overlay is not provided', () => {
        expect(applyProviderCompactOverlay(sourceProvider)).to.equal(sourceProvider);
        expect(getMockProviderForCompact(sourceProvider, 'not-a-compact')).to.equal(sourceProvider);
    });
});
