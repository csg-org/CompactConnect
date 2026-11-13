//
//  mock.data.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 9/24/2026.
//

import { expect } from 'chai';
import { CompactType } from '@models/Compact/Compact.model';
import { LicenseeSerializer } from '@models/Licensee/Licensee.model';
import { Application } from '@models/Application/Application.model';
import { Authorization } from '@models/Authorization/Authorization.model';
import {
    licensees,
    applicantApplications,
    applicantAuthorizations,
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

        if (compactType === CompactType.PSYPACT) {
            expect(provider.applications).to.deep.equal(applicantApplications);
            expect(provider.applications).to.not.equal(applicantApplications);
            expect(provider.authorizations).to.deep.equal(applicantAuthorizations);
            expect(provider.authorizations).to.not.equal(applicantAuthorizations);
        } else {
            expect(provider.applications).to.equal(undefined);
            expect(provider.authorizations).to.equal(undefined);
        }
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
    it('should apply the dietitian overlay', () => {
        expectProviderOverlay(CompactType.DIETITIANS);
    });
    it('should serialize PSYPACT applications and authorizations onto the licensee', () => {
        const licensee = LicenseeSerializer.fromServer(getMockProviderForCompact(sourceProvider, CompactType.PSYPACT));

        expect(licensee.applications).to.have.length(applicantApplications.length);
        expect(licensee.applications?.every((application: any) =>
            application instanceof Application)).to.equal(true);
        expect(licensee.authorizations).to.have.length(applicantAuthorizations.length);
        expect(licensee.authorizations?.every((authorization: any) =>
            authorization instanceof Authorization)).to.equal(true);
    });
    it('should not mutate the shared application mocks between calls', () => {
        const firstProvider = getMockProviderForCompact(sourceProvider, CompactType.PSYPACT);
        const secondProvider = getMockProviderForCompact(sourceProvider, CompactType.PSYPACT);

        firstProvider.applications[0].status = 'mutated';
        firstProvider.authorizations[0].status = 'mutated';

        expect(secondProvider.applications[0].status).to.not.equal('mutated');
        expect(secondProvider.authorizations[0].status).to.not.equal('mutated');
        expect(applicantApplications[0].status).to.not.equal('mutated');
        expect(applicantAuthorizations[0].status).to.not.equal('mutated');
    });
    it('should return the original provider when an overlay is not provided', () => {
        expect(applyProviderCompactOverlay(sourceProvider)).to.equal(sourceProvider);
        expect(getMockProviderForCompact(sourceProvider, 'not-a-compact')).to.equal(sourceProvider);
    });
});
