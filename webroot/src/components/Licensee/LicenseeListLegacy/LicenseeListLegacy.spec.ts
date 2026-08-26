//
//  LicenseeListLegacy.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 7/1/2024.
//

import chaiMatchPattern from 'chai-match-pattern';
import chai from 'chai';
import { mountShallow, mountFull } from '@tests/helpers/setup';
import LicenseeList from '@components/Licensee/LicenseeListLegacy/LicenseeListLegacy.vue';
import { Compact, CompactType } from '@models/Compact/Compact.model';
import { AppModes } from '@/app.config';
import store from '@store/index';
import sinon from 'sinon';

chai.use(chaiMatchPattern);

const { expect } = chai;
const lastKey = 'lastKey';
const prevLastKey = 'prevLastKey';
const allSearchParams = {
    firstName: 'firstName',
    lastName: 'lastName',
    state: 'co',
    licenseNumber: 'ABC123',
    licenseType: 'licensed clinical social worker',
    cuid: 'SWC-9999-9',
};
const populateComponentStorePagingKeys = (component) => {
    component.$store.dispatch('license/setStoreLicenseeLastKey', lastKey);
    component.$store.dispatch('license/setStoreLicenseePrevLastKey', prevLastKey);
};

describe('LicenseeList component', async () => {
    afterEach(async () => {
        await store.dispatch('setAppMode', AppModes.JCC);
        await store.dispatch('license/resetStoreSearch');
    });

    it('should mount the component', async () => {
        const wrapper = await mountShallow(LicenseeList);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(LicenseeList).exists()).to.equal(true);
    });
    it('should successfully re-fetch data with previous paging key if going back a page', async () => {
        const wrapper = await mountShallow(LicenseeList);
        const component = wrapper.vm;
        const fetchListData = sinon.spy();

        component.fetchListData = fetchListData;
        component.isInitialFetchCompleted = true;
        populateComponentStorePagingKeys(component);

        await component.paginationChange({ firstIndex: 0, prevNext: -1 });

        expect(component.prevKey).to.equal(prevLastKey);
        expect(component.nextKey).to.equal('');
        expect(fetchListData.calledOnce).to.equal(true);
    });
    it('should successfully re-fetch data with next paging key if going forward a page', async () => {
        const wrapper = await mountShallow(LicenseeList);
        const component = wrapper.vm;
        const fetchListData = sinon.spy();

        component.fetchListData = fetchListData;
        component.isInitialFetchCompleted = true;
        populateComponentStorePagingKeys(component);

        await component.paginationChange({ firstIndex: 0, prevNext: 1 });

        expect(component.prevKey).to.equal('');
        expect(component.nextKey).to.equal(lastKey);
        expect(fetchListData.calledOnce).to.equal(true);
    });
    it('should successfully re-fetch data when returning to first page', async () => {
        const wrapper = await mountShallow(LicenseeList);
        const component = wrapper.vm;
        const fetchListData = sinon.spy();

        component.fetchListData = fetchListData;
        component.isInitialFetchCompleted = true;
        populateComponentStorePagingKeys(component);

        await component.paginationChange({ firstIndex: 0, prevNext: undefined });

        expect(component.prevKey).to.equal('');
        expect(component.nextKey).to.equal('');
        expect(fetchListData.calledOnce).to.equal(true);
    });
    it('should successfully not re-fetch data if page change before initial fetch completes', async () => {
        const wrapper = await mountShallow(LicenseeList);
        const component = wrapper.vm;
        const fetchListData = sinon.spy();

        component.fetchListData = fetchListData;
        component.isInitialFetchCompleted = false;
        populateComponentStorePagingKeys(component);

        await component.paginationChange({ firstIndex: 0, prevNext: 1 });

        expect(component.prevKey).to.equal('');
        expect(component.nextKey).to.equal(lastKey);
        expect(fetchListData.notCalled).to.equal(true);
    });
    it('should successfully not re-fetch data if page change from search results', async () => {
        const wrapper = await mountShallow(LicenseeList);
        const component = wrapper.vm;
        const fetchListData = sinon.spy();

        component.fetchListData = fetchListData;
        component.isInitialFetchCompleted = true;
        populateComponentStorePagingKeys(component);

        await component.paginationChange({ firstIndex: 0, prevNext: 0 });

        expect(component.prevKey).to.equal('');
        expect(component.nextKey).to.equal('');
        expect(fetchListData.notCalled).to.equal(true);
    });
    it('should successfully fetch data with expected search params (no params)', async () => {
        const wrapper = await mountFull(LicenseeList);
        const component = wrapper.vm;
        const requestConfig = await component.fetchListData();

        expect(requestConfig).to.matchPattern({
            jurisdiction: undefined,
            licenseeFirstName: undefined,
            licenseeLastName: undefined,
            '...': '',
        });
    });
    it('should successfully fetch data with expected search params (all params)', async () => {
        const wrapper = await mountShallow(LicenseeList);
        const component = wrapper.vm;
        const testParams = {
            firstName: 'firstName',
            lastName: 'lastName',
            state: 'state',
        };

        await component.$store.dispatch('user/setCurrentCompact', new Compact({ type: CompactType.ASLP }));
        await component.$store.dispatch('license/setStoreSearch', testParams);

        const requestConfig = await component.fetchListData();

        expect(requestConfig).to.matchPattern({
            compact: CompactType.ASLP,
            jurisdiction: testParams.state,
            licenseeFirstName: testParams.firstName,
            licenseeLastName: testParams.lastName,
            '...': '',
        });
    });
    it('should successfully fetch data with expected search params (all params, social work)', async () => {
        const wrapper = await mountShallow(LicenseeList);
        const component = wrapper.vm;

        await component.$store.dispatch('setAppMode', AppModes.SOCIAL_WORK);
        await component.$store.dispatch('user/setCurrentCompact', new Compact({ type: CompactType.SOCIAL_WORK }));
        await component.$store.dispatch('license/setStoreSearch', allSearchParams);

        const requestConfig = await component.fetchListData();

        expect(requestConfig).to.matchPattern({
            compact: CompactType.SOCIAL_WORK,
            jurisdiction: allSearchParams.state,
            licenseeFirstName: allSearchParams.firstName,
            licenseeLastName: allSearchParams.lastName,
            licenseNumber: allSearchParams.licenseNumber,
            licenseType: allSearchParams.licenseType,
            cuid: allSearchParams.cuid,
            '...': '',
        });
    });
    it('should successfully fetch data with expected search params (all params, cosmetology)', async () => {
        const wrapper = await mountShallow(LicenseeList);
        const component = wrapper.vm;

        await component.$store.dispatch('setAppMode', AppModes.COSMETOLOGY);
        await component.$store.dispatch('user/setCurrentCompact', new Compact({ type: CompactType.COSMETOLOGY }));
        await component.$store.dispatch('license/setStoreSearch', allSearchParams);

        const requestConfig = await component.fetchListData();

        expect(requestConfig).to.matchPattern({
            compact: CompactType.COSMETOLOGY,
            jurisdiction: allSearchParams.state,
            licenseeFirstName: allSearchParams.firstName,
            licenseeLastName: allSearchParams.lastName,
            licenseNumber: allSearchParams.licenseNumber,
            licenseType: undefined,
            cuid: undefined,
            '...': '',
        });
    });
    it('should successfully display license number, license type, and CUID in the search tag', async () => {
        const wrapper = await mountShallow(LicenseeList);
        const component = wrapper.vm;

        await component.$store.dispatch('license/setStoreSearch', {
            firstName: 'Test',
            lastName: 'User',
            state: 'co',
            licenseNumber: allSearchParams.licenseNumber,
            licenseType: allSearchParams.licenseType,
            cuid: allSearchParams.cuid,
        });

        expect(component.searchDisplayLicenseNumber).to.equal(
            `${component.$t('licensing.licenseNumSymbol')}: ${allSearchParams.licenseNumber}`
        );
        expect(component.searchDisplayLicenseType).to.equal('Clinical');
        expect(component.searchDisplayCuid).to.equal(
            `${component.$t('licensing.cuid')}: ${allSearchParams.cuid}`
        );
        expect(component.searchDisplayAll).to.equal([
            'Test User',
            'Colorado',
            component.searchDisplayLicenseNumber,
            component.searchDisplayLicenseType,
            component.searchDisplayCuid,
        ].join(', '));
    });
});
