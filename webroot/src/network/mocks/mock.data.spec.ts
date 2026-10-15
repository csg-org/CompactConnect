//
//  mock.data.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 9/24/2026.
//

import { expect } from 'chai';
import { CompactType } from '@models/Compact/Compact.model';
import { LicenseType } from '@models/License/License.model';
import {
    licensees,
    mockProviderCompactOverlays,
    applyProviderCompactOverlay,
    getMockProviderForCompact
} from '@network/mocks/mock.data';

describe('mock provider compact overlays', () => {
    const sourceProvider = licensees.providers[0];

    it('should leave the shared octp practitioner unchanged when no overlay applies', () => {
        const provider = getMockProviderForCompact(sourceProvider, CompactType.OT);

        expect(provider).to.equal(sourceProvider);
        expect(sourceProvider.compact).to.equal(CompactType.OT);
        expect(sourceProvider.licenseType).to.equal(LicenseType.OCCUPATIONAL_THERAPY_ASSISTANT);
    });
    it('should apply the psypact overlay without mutating the source practitioner', () => {
        const provider = getMockProviderForCompact(sourceProvider, CompactType.PSYPACT);
        const overlay = mockProviderCompactOverlays[CompactType.PSYPACT];

        expect(provider).to.not.equal(sourceProvider);
        expect(provider.compact).to.equal(overlay?.compact);
        expect(provider.licenseType).to.equal(overlay?.licenseType);
        expect(sourceProvider.compact).to.equal(CompactType.OT);
        expect(sourceProvider.licenseType).to.equal(LicenseType.OCCUPATIONAL_THERAPY_ASSISTANT);
        expect(provider.licenses.every((license) => license.compact === CompactType.PSYPACT)).to.equal(true);
        expect(provider.licenses.every((license) => license.licenseType === LicenseType.PSYCHOLOGIST)).to.equal(true);
        expect(provider.privileges.every((privilege) => privilege.compact === CompactType.PSYPACT)).to.equal(true);
        expect(provider.privileges.every((privilege) =>
            privilege.licenseType === LicenseType.PSYCHOLOGIST)).to.equal(true);
        expect(provider.militaryAffiliations.every((affiliation) =>
            affiliation.compact === CompactType.PSYPACT)).to.equal(true);
        expect(provider.militaryAffiliations.every((affiliation) =>
            affiliation.licenseType === undefined)).to.equal(true);
    });
    it('should return the original provider when an overlay is not provided', () => {
        expect(applyProviderCompactOverlay(sourceProvider)).to.equal(sourceProvider);
        expect(getMockProviderForCompact(sourceProvider, 'not-a-compact')).to.equal(sourceProvider);
    });
});
