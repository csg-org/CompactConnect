//
//  PrivilegePurchaseAttestation.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 11/4/2024.
//

import { expect } from 'chai';
import sinon from 'sinon';
import { flushPromises } from '@vue/test-utils';
import { mountShallow } from '@tests/helpers/setup';
import PrivilegePurchaseAttestation from '@components/PrivilegePurchaseAttestation/PrivilegePurchaseAttestation.vue';
import { Compact, CompactType } from '@models/Compact/Compact.model';
import { AcceptedAttestationToSend } from '@models/AcceptedAttestationToSend/AcceptedAttestationToSend.model';
import { PrivilegeAttestation } from '@models/PrivilegeAttestation/PrivilegeAttestation.model';
import { dataApi } from '@network/data.api';
import store from '@store/index';
import { MutationTypes } from '@store/user/user.mutations';

const mountForCompact = async (compactType: CompactType) => {
    sinon.stub(dataApi, 'getAttestation').callsFake(async (_compact, attestationId) => new PrivilegeAttestation({
        id: attestationId,
        version: '1',
        text: String(attestationId),
    }));
    store.commit(`user/${MutationTypes.STORE_UPDATE_CURRENT_COMPACT}`, new Compact({ type: compactType }));

    const wrapper = await mountShallow(PrivilegePurchaseAttestation);

    await flushPromises();

    const component = wrapper.vm;

    if (!component.areFormInputsSet) {
        await component.initFormInputs();
    }

    return component;
};

describe('PrivilegePurchaseAttestation page', async () => {
    it('should mount the page component', async () => {
        const wrapper = await mountShallow(PrivilegePurchaseAttestation);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(PrivilegePurchaseAttestation).exists()).to.equal(true);
    });
    it('should omit the prior-encumbrance attestation for dietitians', async () => {
        const component = await mountForCompact(CompactType.DIETITIANS);
        const attestationIds = component.prepareAttestations().map((attestation: AcceptedAttestationToSend) =>
            attestation.attestationId);

        expect(component.areFormInputsSet).to.equal(true);
        expect(component.showsPriorEncumbranceAttestation).to.equal(false);
        expect(component.formData.disciplinePrior).to.equal(undefined);
        expect(attestationIds).to.not.include('discipline-no-prior-encumbrance-attestation');
        expect(attestationIds).to.include('discipline-no-current-encumbrance-attestation');
    });
    it('should include the prior-encumbrance attestation for occupational therapy', async () => {
        const component = await mountForCompact(CompactType.OT);
        const attestationIds = component.prepareAttestations().map((attestation: AcceptedAttestationToSend) =>
            attestation.attestationId);

        expect(component.areFormInputsSet).to.equal(true);
        expect(component.showsPriorEncumbranceAttestation).to.equal(true);
        expect(component.formData.disciplinePrior).to.not.equal(undefined);
        expect(attestationIds).to.include('discipline-no-prior-encumbrance-attestation');
    });
});
