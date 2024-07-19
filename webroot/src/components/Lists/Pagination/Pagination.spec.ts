//
//  Pagination.spec.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 5/21/2020.
//

import sinon from 'sinon';
import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import Pagination from '@components/Lists/Pagination/Pagination.vue';
// import LeftCaretIcon from '@components/Icons/LeftCaretIcon/LeftCaretIcon.vue';
import RightCaretIcon from '@components/Icons/RightCaretIcon/RightCaretIcon.vue';

describe('Pagination component', async () => {
    it('should mount the component', async () => {
        const wrapper = await mountShallow(Pagination, {
            props: {
                paginationId: 'test',
                pageChange: () => null,
            },
        });

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(Pagination).exists()).to.equal(true);
        // expect(wrapper.findComponent(LeftCaretIcon).exists()).to.equal(true);
        expect(wrapper.findComponent(RightCaretIcon).exists()).to.equal(true);
    });
    it('should load with expected default behavior', async () => {
        const spy = sinon.spy();
        const wrapper = await mountShallow(Pagination, {
            props: {
                paginationId: 'test',
                pageChange: spy,
                listSize: 0,
            }
        });
        const instance = wrapper.vm;

        expect(instance.currentPage).to.equal(1);
        expect(spy.calledOnce).to.be.true;
        expect(spy.withArgs(0, 25).calledOnce).to.be.true;
        expect(instance.pageCount).to.equal(0);
    });
    // Temp for limited server paging support
    // it('should load with expected behavior based on list size', async () => {
    //     const spy = sinon.spy();
    //     const wrapper = await mountShallow(Pagination, {
    //         props: {
    //             paginationId: 'test',
    //             pageChange: spy,
    //             listSize: 32,
    //         }
    //     });
    //     const instance = wrapper.vm;
    //
    //     expect(instance.currentPage).to.equal(1);
    //     expect(spy.calledOnce).to.be.true;
    //     expect(spy.withArgs(0, 5).calledOnce).to.be.true;
    //     expect(instance.pageCount).to.equal(7);
    // });
    // it('should call pageChange with the new page size', async () => {
    //     const spy = sinon.spy();
    //     const wrapper = await mountShallow(Pagination, {
    //         props: {
    //             paginationId: 'test',
    //             pageChange: spy,
    //             listSize: 18,
    //         }
    //     });
    //     const instance = wrapper.vm as any;
    //
    //     instance.setSize({ value: 10 });
    //
    //     expect(instance.isFirstPage).to.be.true;
    //     expect(instance.currentPage).to.equal(1);
    //     expect(instance.pageCount).to.equal(2);
    //     expect(instance.isLastPage).to.be.false;
    //     expect(spy.withArgs(0, 10).calledOnce).to.be.true;
    //
    //     instance.setSize({ value: 20 });
    //
    //     expect(instance.isFirstPage).to.be.true;
    //     expect(instance.currentPage).to.equal(1);
    //     expect(instance.pageCount).to.equal(1);
    //     expect(instance.isLastPage).to.be.true;
    //     expect(spy.withArgs(0, 20).calledOnce).to.be.true;
    //
    //     expect(spy.calledThrice).to.be.true; // Since it's called on mount as well.
    // });
    // it('should return an array with one page when the list size is one', async () => {
    //     const spy = sinon.spy();
    //     const wrapper = await mountShallow(Pagination, {
    //         props: {
    //             paginationId: 'test',
    //             pageChange: spy,
    //             listSize: 1,
    //         }
    //     });
    //     const instance = wrapper.vm;
    //     const { pages } = instance;
    //
    //     expect(instance.isFirstPage).to.be.true;
    //     expect(instance.isLastPage).to.be.true;
    //     expect(pages).to.be.an('array');
    //     expect(pages).to.have.length(1);
    // });
    // it('should return an array of [1, 2, 3, 4, 5, ..., 19] when the list size is 94, and the current page is 1 at size 5', async () => {
    //     const spy = sinon.spy();
    //     const wrapper = await mountShallow(Pagination, {
    //         props: {
    //             paginationId: 'test1',
    //             pageChange: spy,
    //             listSize: 94,
    //         }
    //     });
    //     const instance = wrapper.vm;
    //     const pages = instance.pages.map((page) => page.displayValue);
    //
    //     expect(pages).to.be.an('array');
    //     expect(pages).to.have.length(7);
    //     expect(pages[0]).to.equal(1);
    //     expect(pages[1]).to.equal(2);
    //     expect(pages[2]).to.equal(3);
    //     expect(pages[3]).to.equal(4);
    //     expect(pages[4]).to.equal(5);
    //     expect(pages[5]).to.equal('...');
    //     expect(pages[6]).to.equal(19);
    // });
    // it('should return an array of [1, 2, 3, 4, 5, ..., 19] when the list size is 94, and the current page is 3 at size 5', async () => {
    //     const spy = sinon.spy();
    //     const wrapper = await mountShallow(Pagination, {
    //         props: {
    //             paginationId: 'test1',
    //             pageChange: spy,
    //             listSize: 94,
    //         }
    //     });
    //     const instance = wrapper.vm;
    //
    //     instance.setPage(3);
    //
    //     const pages = instance.pages.map((page) => page.displayValue);
    //
    //     expect(pages).to.be.an('array');
    //     expect(pages).to.have.length(7);
    //     expect(pages[0]).to.equal(1);
    //     expect(pages[1]).to.equal(2);
    //     expect(pages[2]).to.equal(3);
    //     expect(pages[3]).to.equal(4);
    //     expect(pages[4]).to.equal(5);
    //     expect(pages[5]).to.equal('...');
    //     expect(pages[6]).to.equal(19);
    // });
    // it('should return an array of [1, ..., 3, 4, 5, ..., 19] when the list size is 94, and the current page is 4 at size 5', async () => {
    //     const spy = sinon.spy();
    //     const wrapper = await mountShallow(Pagination, {
    //         props: {
    //             paginationId: 'test1',
    //             pageChange: spy,
    //             listSize: 94,
    //         }
    //     });
    //     const instance = wrapper.vm;
    //
    //     instance.setPage(4);
    //
    //     const pages = instance.pages.map((page) => page.displayValue);
    //
    //     expect(pages).to.be.an('array');
    //     expect(pages).to.have.length(7);
    //     expect(pages[0]).to.equal(1);
    //     expect(pages[1]).to.equal('...');
    //     expect(pages[2]).to.equal(3);
    //     expect(pages[3]).to.equal(4);
    //     expect(pages[4]).to.equal(5);
    //     expect(pages[5]).to.equal('...');
    //     expect(pages[6]).to.equal(19);
    // });
    // it('should return an array of [1, ..., 15, 16, 17, ..., 19] when the list size is 94, and the current page is 16 at size 5', async () => {
    //     const spy = sinon.spy();
    //     const wrapper = await mountShallow(Pagination, {
    //         props: {
    //             paginationId: 'test1',
    //             pageChange: spy,
    //             listSize: 94,
    //         }
    //     });
    //     const instance = wrapper.vm;
    //
    //     instance.setPage(16);
    //
    //     const pages = instance.pages.map((page) => page.displayValue);
    //
    //     expect(pages).to.be.an('array');
    //     expect(pages).to.have.length(7);
    //     expect(pages[0]).to.equal(1);
    //     expect(pages[1]).to.equal('...');
    //     expect(pages[2]).to.equal(15);
    //     expect(pages[3]).to.equal(16);
    //     expect(pages[4]).to.equal(17);
    //     expect(pages[5]).to.equal('...');
    //     expect(pages[6]).to.equal(19);
    // });
    // it('should return an array of [1, ..., 15, 16, 17, 18, 19] when the list size is 94, and the current page is 17 at size 5', async () => {
    //     const spy = sinon.spy();
    //     const wrapper = await mountShallow(Pagination, {
    //         props: {
    //             paginationId: 'test1',
    //             pageChange: spy,
    //             listSize: 94,
    //         }
    //     });
    //     const instance = wrapper.vm as any;
    //
    //     instance.setPage(17);
    //
    //     const pages = instance.pages.map((page) => page.displayValue);
    //
    //     expect(pages).to.be.an('array');
    //     expect(pages).to.have.length(7);
    //     expect(pages[0]).to.equal(1);
    //     expect(pages[1]).to.equal('...');
    //     expect(pages[2]).to.equal(15);
    //     expect(pages[3]).to.equal(16);
    //     expect(pages[4]).to.equal(17);
    //     expect(pages[5]).to.equal(18);
    //     expect(pages[6]).to.equal(19);
    // });
    // it('should return an array of [1, ..., 15, 16, 17, 18, 19] when the list size is 94, and the current page is 19 at size 5', async () => {
    //     const spy = sinon.spy();
    //     const wrapper = await mountShallow(Pagination, {
    //         props: {
    //             paginationId: 'test1',
    //             pageChange: spy,
    //             listSize: 94,
    //         }
    //     });
    //     const instance = wrapper.vm as any;
    //
    //     instance.setPage(19);
    //
    //     const pages = instance.pages.map((page) => page.displayValue);
    //
    //     expect(pages).to.be.an('array');
    //     expect(pages).to.have.length(7);
    //     expect(pages[0]).to.equal(1);
    //     expect(pages[1]).to.equal('...');
    //     expect(pages[2]).to.equal(15);
    //     expect(pages[3]).to.equal(16);
    //     expect(pages[4]).to.equal(17);
    //     expect(pages[5]).to.equal(18);
    //     expect(pages[6]).to.equal(19);
    // });
    // it('should return an array of [1, 2, 3, 4, 5, 6, 7] when the list size is 34, and the current page is 5 at size 5', async () => {
    //     const spy = sinon.spy();
    //     const wrapper = await mountShallow(Pagination, {
    //         props: {
    //             paginationId: 'test1',
    //             pageChange: spy,
    //             listSize: 34,
    //         }
    //     });
    //     const instance = wrapper.vm as any;
    //
    //     instance.setPage(5);
    //
    //     const pages = instance.pages.map((page) => page.displayValue);
    //
    //     expect(pages).to.be.an('array');
    //     expect(pages).to.have.length(7);
    //     expect(pages[0]).to.equal(1);
    //     expect(pages[1]).to.equal(2);
    //     expect(pages[2]).to.equal(3);
    //     expect(pages[3]).to.equal(4);
    //     expect(pages[4]).to.equal(5);
    //     expect(pages[5]).to.equal(6);
    //     expect(pages[6]).to.equal(7);
    // });
    // it('should return an array of [1, 2, 3, 4] when the list size is 18, and the current page is 1 at size 5', async () => {
    //     const spy = sinon.spy();
    //     const wrapper = await mountShallow(Pagination, {
    //         props: {
    //             paginationId: 'test1',
    //             pageChange: spy,
    //             listSize: 18,
    //         }
    //     });
    //     const instance = wrapper.vm;
    //
    //     const pages = instance.pages.map((page) => page.displayValue);
    //
    //     expect(pages).to.be.an('array');
    //     expect(pages).to.have.length(4);
    //     expect(pages[0]).to.equal(1);
    //     expect(pages[1]).to.equal(2);
    //     expect(pages[2]).to.equal(3);
    //     expect(pages[3]).to.equal(4);
    // });
    // it('should have the same pages when pagination ids are same between different components', async () => {
    //     const spy = sinon.spy();
    //     const wrapper1 = await mountShallow(Pagination, {
    //         props: {
    //             paginationId: 'test2',
    //             pageChange: spy,
    //             listSize: 38,
    //         }
    //     });
    //     const wrapper2 = await mountShallow(Pagination, {
    //         props: {
    //             paginationId: 'test2',
    //             pageChange: spy,
    //             listSize: 38,
    //         }
    //     });
    //     const instanceOne = wrapper1.vm;
    //     const instanceTwo = wrapper2.vm;
    //
    //     expect(instanceOne.currentPage).to.equal(instanceTwo.currentPage);
    //     expect(instanceOne.pageSize).to.equal(instanceTwo.pageSize);
    //     expect(spy.calledTwice).to.be.true;
    //
    //     spy.resetHistory();
    //     instanceOne.setPage(3);
    //
    //     expect(instanceOne.currentPage).to.equal(instanceTwo.currentPage);
    //     expect(instanceOne.pageSize).to.equal(instanceTwo.pageSize);
    //     expect(spy.calledOnce).to.be.true;
    //
    //     spy.resetHistory();
    //     instanceOne.setSize({ value: 20 });
    //
    //     expect(instanceOne.currentPage).to.equal(instanceTwo.currentPage);
    //     expect(instanceOne.pageSize).to.equal(instanceTwo.pageSize);
    //     expect(spy.calledOnce).to.be.true;
    // });
    // it('should set the page to the last page when the page size change creates a larger page than exists', async () => {
    //     const spy = sinon.spy();
    //     const wrapper = await mountShallow(Pagination, {
    //         props: {
    //             paginationId: 'test3',
    //             pageChange: spy,
    //             listSize: 38,
    //         }
    //     });
    //     const instance = wrapper.vm;
    //
    //     instance.setPage(4);
    //     instance.setSize({ value: 50 });
    //
    //     const thirdSpy = spy.thirdCall;
    //
    //     expect(thirdSpy.calledWith(0, 50)).to.be.true;
    //     expect(instance.currentPage).to.equal(1);
    // });
});
