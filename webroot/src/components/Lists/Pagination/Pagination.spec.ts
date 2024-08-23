//
//  Pagination.spec.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 5/21/2020.
//

import sinon from 'sinon';
import { expect } from 'chai';
import { mountShallow, mountFull } from '@tests/helpers/setup';
import Pagination from '@components/Lists/Pagination/Pagination.vue';
import LeftCaretIcon from '@components/Icons/LeftCaretIcon/LeftCaretIcon.vue';
import RightCaretIcon from '@components/Icons/RightCaretIcon/RightCaretIcon.vue';

describe('Pagination component', async () => {
    it('should mount the component', async () => {
        const wrapper = await mountShallow(Pagination, {
            props: {
                paginationId: 'test',
                pageChange: () => null,
                pagingPrevKey: '',
                pagingNextKey: '',
            },
        });

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(Pagination).exists()).to.equal(true);
        expect(wrapper.findComponent(LeftCaretIcon).exists()).to.equal(false);
        expect(wrapper.findComponent(RightCaretIcon).exists()).to.equal(false);
    });
    it('should load with expected default behavior', async () => {
        const spy = sinon.spy();
        const wrapper = await mountShallow(Pagination, {
            props: {
                paginationId: 'test',
                pageChange: spy,
                listSize: 0,
                pagingPrevKey: '',
                pagingNextKey: '',
            }
        });
        const instance = wrapper.vm;

        expect(instance.currentPage).to.equal(1);
        expect(spy.calledOnce).to.be.true;
        expect(spy.withArgs(0, 25).calledOnce).to.be.true;
        expect(instance.pageCount).to.equal(0);
    });
    it('should load with previous next paging', async () => {
        const spy = sinon.spy();
        const wrapper = await mountFull(Pagination, {
            props: {
                paginationId: 'test',
                pageChange: spy,
                pagingPrevKey: '',
                pagingNextKey: 'test-next',
            },
        });
        const instance = wrapper.vm;
        const pages = instance.pages.map((page) => page.displayValue);

        expect(pages).to.be.an('array');
        expect(pages).to.have.length(1);
        expect(pages[0]).to.equal(1);
        expect(wrapper.findComponent(LeftCaretIcon).exists(), 'previous arrow').to.equal(false);
        expect(wrapper.findComponent(RightCaretIcon).exists(), 'next arrow').to.equal(true);
    });
    it('should advance with next page (2)', async () => {
        const spy = sinon.spy();
        const wrapper = await mountFull(Pagination, {
            props: {
                paginationId: 'test',
                pageChange: spy,
                pagingPrevKey: 'test-prev',
                pagingNextKey: 'test-next',
            },
        });
        const instance = wrapper.vm;

        await wrapper.get('.pagination-item.next').trigger('click');

        const pages = instance.pages.map((page) => page.displayValue);

        expect(pages).to.be.an('array');
        expect(pages).to.have.length(2);
        expect(pages[0]).to.equal(1);
        expect(pages[1]).to.equal(2);
        expect(wrapper.findComponent(LeftCaretIcon).exists(), 'previous arrow').to.equal(true);
        expect(wrapper.findComponent(RightCaretIcon).exists(), 'next arrow').to.equal(true);
    });
    it('should advance with next page (3)', async () => {
        const spy = sinon.spy();
        const wrapper = await mountFull(Pagination, {
            props: {
                paginationId: 'test',
                pageChange: spy,
                pagingPrevKey: 'test-prev',
                pagingNextKey: 'test-next',
            },
        });
        const instance = wrapper.vm;

        await wrapper.get('.pagination-item.next').trigger('click');

        const pages = instance.pages.map((page) => page.displayValue);

        expect(pages).to.be.an('array');
        expect(pages).to.have.length(3);
        expect(pages[0]).to.equal(1);
        expect(pages[1]).to.equal('...');
        expect(pages[2]).to.equal(3);
        expect(wrapper.findComponent(LeftCaretIcon).exists(), 'previous arrow').to.equal(true);
        expect(wrapper.findComponent(RightCaretIcon).exists(), 'next arrow').to.equal(true);
    });
    it('should revert with previous page (2)', async () => {
        const spy = sinon.spy();
        const wrapper = await mountFull(Pagination, {
            props: {
                paginationId: 'test',
                pageChange: spy,
                pagingPrevKey: 'test-prev',
                pagingNextKey: 'test-next',
            },
        });
        const instance = wrapper.vm;

        await wrapper.get('.pagination-item.previous').trigger('click');

        const pages = instance.pages.map((page) => page.displayValue);

        expect(pages).to.be.an('array');
        expect(pages).to.have.length(2);
        expect(pages[0]).to.equal(1);
        expect(pages[1]).to.equal(2);
        expect(wrapper.findComponent(LeftCaretIcon).exists(), 'previous arrow').to.equal(true);
        expect(wrapper.findComponent(RightCaretIcon).exists(), 'next arrow').to.equal(true);
    });
    it('should revert with previous page (1)', async () => {
        const spy = sinon.spy();
        const wrapper = await mountFull(Pagination, {
            props: {
                paginationId: 'test',
                pageChange: spy,
                pagingPrevKey: 'test-prev',
                pagingNextKey: 'test-next',
            },
        });
        const instance = wrapper.vm;

        await wrapper.get('.pagination-item.previous').trigger('click');

        const pages = instance.pages.map((page) => page.displayValue);

        expect(pages).to.be.an('array');
        expect(pages).to.have.length(1);
        expect(pages[0]).to.equal(1);
        expect(wrapper.findComponent(LeftCaretIcon).exists(), 'previous arrow').to.equal(false);
        expect(wrapper.findComponent(RightCaretIcon).exists(), 'next arrow').to.equal(true);
    });
});
