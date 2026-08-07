//
//  PrivilegeCard.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 10/8/2024.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import PrivilegeCard from '@components/PrivilegeCard/PrivilegeCard.vue';
import { AppModes, getEncumberConfigPrivilege } from '@/app.config';

describe('PrivilegeCard component', async () => {
    it('should mount the component', async () => {
        const wrapper = await mountShallow(PrivilegeCard);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(PrivilegeCard).exists()).to.equal(true);
    });
    it('should successfully return expected encumber config for privilege (jcc)', async () => {
        const config = getEncumberConfigPrivilege(AppModes.JCC);

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
            'surrender of privilege',
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
    it('should successfully return expected encumber config for privilege (cosmetology)', async () => {
        const config = getEncumberConfigPrivilege(AppModes.COSMETOLOGY);

        expect(config.disciplineTypes).to.eql([
            'suspension',
            'revocation',
            'surrender of privilege',
        ]);
        expect(config.npdbTypes).to.eql([
            'fraud',
            'consumer harm',
            'other',
        ]);
    });
    it('should successfully return expected encumber config for privilege (social-work)', async () => {
        const config = getEncumberConfigPrivilege(AppModes.SOCIAL_WORK);

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
            'surrender of privilege',
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
