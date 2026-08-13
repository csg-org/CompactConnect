//
//  LicenseCard.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 10/8/2024.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import LicenseCard from '@components/LicenseCard/LicenseCard.vue';
import { AppModes, getEncumberConfigLicense } from '@/app.config';

describe('LicenseCard component', async () => {
    it('should mount the component', async () => {
        const wrapper = await mountShallow(LicenseCard);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(LicenseCard).exists()).to.equal(true);
    });
    it('should successfully return expected encumber config for license (jcc)', async () => {
        const config = getEncumberConfigLicense(AppModes.JCC);

        expect(config.disciplineTypes).to.eql([
            'fine',
            'reprimand',
            'required supervision',
            'completion of continuing education',
            'public reprimand',
            'probation',
            'injunctive action',
            'suspension',
            'revocation',
            'denial',
            'surrender of license',
            'modification of previous action-extension',
            'modification of previous action-reduction',
            'other monitoring',
            'other adjudicated action not listed',
        ]);
        expect(config.npdbTypes).to.eql([
            'Non-compliance With Requirements',
            'Criminal Conviction or Adjudication',
            'Confidentiality, Consent or Disclosure Violations',
            'Misconduct or Abuse',
            'Fraud, Deception, or Misrepresentation',
            'Unsafe Practice or Substandard Care',
            'Improper Supervision or Allowing Unlicensed Practice',
            'Other',
        ]);
    });
    it('should successfully return expected encumber config for license (cosmetology)', async () => {
        const config = getEncumberConfigLicense(AppModes.COSMETOLOGY);

        expect(config.disciplineTypes).to.eql([
            'suspension',
            'revocation',
            'surrender of license',
        ]);
        expect(config.npdbTypes).to.eql([
            'fraud',
            'consumer harm',
            'other',
        ]);
    });
    it('should successfully return expected encumber config for license (social-work)', async () => {
        const config = getEncumberConfigLicense(AppModes.SOCIAL_WORK);

        expect(config.disciplineTypes).to.eql([
            'fine',
            'reprimand',
            'required supervision',
            'completion of continuing education',
            'public reprimand',
            'probation',
            'injunctive action',
            'suspension',
            'revocation',
            'denial',
            'surrender of license',
            'modification of previous action-extension',
            'modification of previous action-reduction',
            'other monitoring',
            'other adjudicated action not listed',
        ]);
        expect(config.npdbTypes).to.eql([
            'Non-compliance With Requirements',
            'Conflict of Interest',
            'Substandard Care or Patient Neglect/Abuse',
            'Criminal Conviction or Adjudication',
            'Confidentiality, Consent or Disclosure Violations',
            'Fraud, Deception, or Misrepresentation',
            'Improper Supervision or Allowing Unlicensed Practice',
            'Improper Prescribing, Dispensing, Administering Medication/Drug Violation',
            'Other',
        ]);
    });
});
