//
//  LicenseeList.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 7/1/2024.
//

import chaiMatchPattern from 'chai-match-pattern';
import chai from 'chai';
import { mountShallow, mountFull } from '@tests/helpers/setup';
import LicenseeList from '@components/Licensee/LicenseeList/LicenseeList.vue';
import { Compact, CompactType } from '@models/Compact/Compact.model';
import sinon from 'sinon';

chai.use(chaiMatchPattern);

const { expect } = chai;
const lastKey = 'lastKey';
const prevLastKey = 'prevLastKey';
const populateComponentStorePagingKeys = (component) => {
    component.$store.dispatch('license/setStoreLicenseeLastKey', lastKey);
    component.$store.dispatch('license/setStoreLicenseePrevLastKey', prevLastKey);
};

describe('LicenseeList component', async () => {
    before(() => {
        global.requestAnimationFrame = (cb) => cb(); // JSDOM omits this global method, so we need to mock it ourselves
    });
    it('should mount the component', async () => {
        const wrapper = await mountFull(LicenseeList); // mounting full here to get ahead of some vue-test-utils oddities in fast local environments

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
        const wrapper = await mountShallow(LicenseeList);
        const component = wrapper.vm;
        const requestConfig = await component.fetchListData();

        expect(requestConfig).to.matchPattern({
            compact: undefined,
            jurisdiction: undefined,
            licenseeFirstName: undefined,
            licenseeLastName: undefined,
            licenseeSsn: undefined,
            '...': '',
        });
    });
    it('should successfully fetch data with expected search params (all params)', async () => {
        const wrapper = await mountShallow(LicenseeList);
        const component = wrapper.vm;
        const testParams = {
            firstName: 'firstName',
            lastName: 'lastName',
            ssn: 'ssn',
            state: 'state',
        };

        await component.$store.dispatch('user/setCurrentCompact', new Compact({ type: CompactType.ASLP }));

        const requestConfig = await component.fetchListData(testParams);

        expect(requestConfig).to.matchPattern({
            compact: CompactType.ASLP,
            jurisdiction: testParams.state,
            licenseeFirstName: testParams.firstName,
            licenseeLastName: testParams.lastName,
            licenseeSsn: testParams.ssn,
            '...': '',
        });
    });
});
