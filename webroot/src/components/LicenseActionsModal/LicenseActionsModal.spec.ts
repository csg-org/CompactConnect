//
//  LicenseActionsModal.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 9/23/2026.
//

import { expect } from 'chai';
import sinon from 'sinon';
import { mountShallow } from '@tests/helpers/setup';
import LicenseActionsModal from '@components/LicenseActionsModal/LicenseActionsModal.vue';
import { Compact, CompactType } from '@models/Compact/Compact.model';
import { State } from '@models/State/State.model';
import { License, LicenseStatus } from '@models/License/License.model';
import { Licensee } from '@models/Licensee/Licensee.model';
import { Investigation } from '@models/Investigation/Investigation.model';
import { StaffUser, CompactPermission, StatePermission } from '@models/StaffUser/StaffUser.model';
import { MutationTypes } from '@store/user/user.mutations';

const compactType = CompactType.ASLP;
const stateAbbrev = 'ky';

const buildLicense = (overrides: Record<string, unknown> = {}): License => new License({
    id: 'provider-ky-audiologist',
    licenseeId: 'provider',
    issueState: new State({ abbrev: stateAbbrev }),
    status: LicenseStatus.ACTIVE,
    licenseNumber: '123',
    ...overrides,
});

const buildLicensee = (): Licensee => new Licensee({
    firstName: 'Test',
    lastName: 'Practitioner',
});

const buildCompactPermission = (
    compactOverrides: Partial<CompactPermission> = {},
    stateOverrides: Array<Partial<StatePermission>> = []
): CompactPermission => ({
    compact: new Compact({ type: compactType }),
    isReadPrivate: false,
    isReadSsn: false,
    isAdmin: false,
    states: stateOverrides.map((stateOverride) => ({
        state: { abbrev: stateAbbrev } as any,
        isReadPrivate: false,
        isReadSsn: false,
        isWrite: false,
        isAdmin: false,
        ...stateOverride,
    })),
    ...compactOverrides,
});

const setCurrentUser = (wrapper, compactPermission: CompactPermission): void => {
    wrapper.vm.$store.commit(`user/${MutationTypes.STORE_UPDATE_CURRENT_COMPACT}`, new Compact({ type: compactType }));
    wrapper.vm.$store.commit(`user/${MutationTypes.STORE_UPDATE_USER}`, new StaffUser({
        permissions: [compactPermission],
    }));
};

const mountActions = async (props: Record<string, unknown> = {}) => mountShallow(LicenseActionsModal, {
    props: {
        license: buildLicense(),
        licensee: buildLicensee(),
        ...props,
    },
});

describe('LicenseActionsModal component', async () => {
    it('should mount the component', async () => {
        const wrapper = await mountActions();

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(LicenseActionsModal).exists()).to.equal(true);
    });
    it('should hide the action menu when the user has no admin permissions', async () => {
        const wrapper = await mountActions();

        expect(wrapper.vm.shouldShowMenu).to.equal(false);
        expect(wrapper.find('.license-actions-menu-toggle').exists()).to.equal(false);
    });
    it('should show license discipline items for a state admin and hide deactivate', async () => {
        const wrapper = await mountActions();

        setCurrentUser(wrapper, buildCompactPermission({}, [{ isAdmin: true }]));
        await wrapper.vm.toggleLicenseActionMenu();
        await wrapper.vm.$nextTick();

        expect(wrapper.vm.shouldShowMenu).to.equal(true);
        expect(wrapper.vm.shouldShowDeactivateMenuItem).to.equal(false);
        expect(wrapper.vm.shouldShowDisciplineMenuItems).to.equal(true);
        expect(wrapper.find('.license-actions-menu-toggle').exists()).to.equal(true);

        const items = wrapper.findAll('.license-menu-item').map((item) => item.text());

        expect(items).to.include(wrapper.vm.$t('licensing.encumber'));
        expect(items).to.include(wrapper.vm.$t('licensing.addInvestigation'));
        expect(items).to.not.include(wrapper.vm.$t('licensing.deactivate'));
    });
    it('should hide the license menu for a compact admin who is not a state admin', async () => {
        const wrapper = await mountActions();

        setCurrentUser(wrapper, buildCompactPermission({ isAdmin: true }));

        expect(wrapper.vm.shouldShowMenu).to.equal(false);
        expect(wrapper.vm.shouldShowDeactivateMenuItem).to.equal(false);
        expect(wrapper.vm.shouldShowDisciplineMenuItems).to.equal(false);
    });
    it('should show deactivate for a privilege compact admin and hide encumber', async () => {
        const wrapper = await mountActions({ type: 'privilege' });

        setCurrentUser(wrapper, buildCompactPermission({ isAdmin: true }));
        await wrapper.vm.toggleLicenseActionMenu();
        await wrapper.vm.$nextTick();

        expect(wrapper.vm.shouldShowMenu).to.equal(true);
        expect(wrapper.vm.shouldShowDeactivateMenuItem).to.equal(true);
        expect(wrapper.vm.shouldShowDisciplineMenuItems).to.equal(false);

        const items = wrapper.findAll('.license-menu-item').map((item) => item.text());

        expect(items).to.include(wrapper.vm.$t('licensing.deactivate'));
        expect(items).to.not.include(wrapper.vm.$t('licensing.encumber'));
    });
    it('should show privilege discipline items for a state admin and hide deactivate', async () => {
        const wrapper = await mountActions({ type: 'privilege' });

        setCurrentUser(wrapper, buildCompactPermission({}, [{ isAdmin: true }]));
        await wrapper.vm.toggleLicenseActionMenu();
        await wrapper.vm.$nextTick();

        expect(wrapper.vm.shouldShowMenu).to.equal(true);
        expect(wrapper.vm.shouldShowDeactivateMenuItem).to.equal(false);
        expect(wrapper.vm.shouldShowDisciplineMenuItems).to.equal(true);

        const items = wrapper.findAll('.license-menu-item').map((item) => item.text());

        expect(items).to.include(wrapper.vm.$t('licensing.encumber'));
        expect(items).to.not.include(wrapper.vm.$t('licensing.deactivate'));
    });
    it('should show unencumber and end investigation only when those statuses apply', async () => {
        const investigation = new Investigation({
            id: 'inv-1',
            startDate: '2026-01-01',
        });
        const wrapper = await mountActions({
            license: buildLicense({
                adverseActions: [{ id: 'aa-1', isActive: () => true, endDate: null }] as any,
                investigations: [investigation],
            }),
        });

        setCurrentUser(wrapper, buildCompactPermission({}, [{ isAdmin: true }]));
        wrapper.vm.license.isEncumbered = () => true;
        wrapper.vm.license.isUnderInvestigation = () => true;
        await wrapper.vm.toggleLicenseActionMenu();
        await wrapper.vm.$nextTick();

        const items = wrapper.findAll('.license-menu-item').map((item) => item.text());

        expect(items).to.include(wrapper.vm.$t('licensing.unencumber'));
        expect(items).to.include(wrapper.vm.$t('licensing.endInvestigation'));
    });
    it('should prefix element IDs with the license model id', async () => {
        const wrapper = await mountActions();

        expect(wrapper.vm.idPrefix).to.equal('provider-ky-audiologist');
        expect(wrapper.vm.ids.disciplineAction).to.equal('discipline-action-provider-ky-audiologist');
    });
    it('should fall back to an instance id when the license has no model id', async () => {
        const wrapper = await mountActions({
            license: buildLicense({ id: null }),
        });

        expect(wrapper.vm.idPrefix).to.match(/^license-actions-\d+$/);
    });
    it('should clear selectedInvestigation when opening encumber from the menu', async () => {
        const wrapper = await mountActions();
        const investigation = new Investigation({ id: 'inv-1', startDate: '2026-01-01' });

        wrapper.vm.selectedInvestigation = investigation;
        wrapper.vm.openEncumberFromMenu();

        expect(wrapper.vm.selectedInvestigation).to.equal(null);
        expect(wrapper.vm.isEncumberLicenseModalDisplayed).to.equal(true);
        expect(wrapper.vm.isLicenseActionMenuDisplayed).to.equal(false);
    });
    it('should keep selectedInvestigation when ending an investigation with encumbrance', async () => {
        const wrapper = await mountActions();
        const investigation = new Investigation({ id: 'inv-1', startDate: '2026-01-01' });

        wrapper.vm.selectedInvestigation = investigation;
        wrapper.vm.isEndInvestigationModalDisplayed = true;
        wrapper.vm.submitEndInvestigationWithEncumbrance();

        expect(wrapper.vm.selectedInvestigation?.id).to.equal(investigation.id);
        expect(wrapper.vm.isEndInvestigationModalDisplayed).to.equal(false);
        expect(wrapper.vm.isEncumberLicenseModalDisplayed).to.equal(true);
    });
    it('should clear selectedInvestigation when the encumber modal is closed', async () => {
        const wrapper = await mountActions();
        const investigation = new Investigation({ id: 'inv-1', startDate: '2026-01-01' });

        wrapper.vm.selectedInvestigation = investigation;
        wrapper.vm.isEncumberLicenseModalDisplayed = true;
        wrapper.vm.closeEncumberLicenseModal();

        expect(wrapper.vm.selectedInvestigation).to.equal(null);
        expect(wrapper.vm.isEncumberLicenseModalDisplayed).to.equal(false);
    });
    it('should dispatch encumberLicenseRequest for a standalone license encumber', async () => {
        const wrapper = await mountActions();
        const dispatch = sinon.stub(wrapper.vm.$store, 'dispatch').resolves();

        wrapper.vm.isEncumberLicenseModalDisplayed = true;
        wrapper.vm.initFormInputsEncumberLicense();
        sinon.stub(wrapper.vm, 'validateAll');
        wrapper.vm.isFormValid = true;
        await wrapper.vm.submitEncumberLicense();

        expect(dispatch.calledWith('users/encumberLicenseRequest')).to.equal(true);
        expect(dispatch.calledWith('users/updateInvestigationLicenseRequest')).to.equal(false);
        dispatch.restore();
    });
    it('should dispatch updateInvestigationLicenseRequest when encumbering from an investigation', async () => {
        const wrapper = await mountActions();
        const dispatch = sinon.stub(wrapper.vm.$store, 'dispatch').resolves();
        const investigation = new Investigation({ id: 'inv-1', startDate: '2026-01-01' });

        wrapper.vm.selectedInvestigation = investigation;
        wrapper.vm.isEncumberLicenseModalDisplayed = true;
        wrapper.vm.initFormInputsEncumberLicense();
        sinon.stub(wrapper.vm, 'validateAll');
        wrapper.vm.isFormValid = true;
        await wrapper.vm.submitEncumberLicense();

        expect(dispatch.calledWith('users/updateInvestigationLicenseRequest')).to.equal(true);
        expect(dispatch.calledWith('users/encumberLicenseRequest')).to.equal(false);
        dispatch.restore();
    });
    it('should dispatch privilege store actions when type is privilege', async () => {
        const wrapper = await mountActions({ type: 'privilege' });
        const dispatch = sinon.stub(wrapper.vm.$store, 'dispatch').resolves();

        wrapper.vm.isEncumberLicenseModalDisplayed = true;
        wrapper.vm.initFormInputsEncumberLicense();
        sinon.stub(wrapper.vm, 'validateAll');
        wrapper.vm.isFormValid = true;
        await wrapper.vm.submitEncumberLicense();

        expect(dispatch.calledWith('users/encumberPrivilegeRequest')).to.equal(true);
        expect(dispatch.calledWith('users/encumberLicenseRequest')).to.equal(false);
        dispatch.restore();
    });
    it('should default type to license', async () => {
        const wrapper = await mountActions();

        expect(wrapper.vm.type).to.equal('license');
        expect(wrapper.vm.isPrivilege).to.equal(false);
        expect(wrapper.vm.i18nNoun).to.equal('License');
        expect(wrapper.vm.storeNoun).to.equal('License');
    });
});
