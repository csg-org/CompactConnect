//
//  Modal.spec.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 5/22/2020.
//  Copyright © 2024. InspiringApps. All rights reserved.
//

import { expect } from 'chai';
import sinon from 'sinon';
import { mountShallow } from '@tests/helpers';
import Modal from '@components/Modal/Modal.vue';

describe('Modal component', async () => {
    it('should mount the component', async () => {
        const wrapper = await mountShallow(Modal);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(Modal).exists()).to.equal(true);
    });
    it('should mount with default properties', async () => {
        const wrapper = await mountShallow(Modal);
        const component = wrapper.vm;

        component.closeModal = sinon.spy();

        expect(component.title).to.equal('');
        expect(wrapper.find('.modal-mask').text()).to.equal('Info:');

        expect(component.closeOnBackgroundClick).to.equal(false);
        wrapper.find('.modal-mask').trigger('click');
        expect(component.closeModal.called).to.equal(false);

        expect(component.hasCloseIcon).to.equal(false);
        expect(wrapper.find('.icon-close-modal').exists()).to.equal(false);

        expect(component.isErrorModal).to.equal(false);
        expect(wrapper.find('.modal-container').classes()).to.not.contain('modal-error');

        expect(component.showActions).to.equal(true);
        expect(wrapper.find('.modal-actions').exists()).to.equal(true);

        expect(component.customActions).to.be.an('array').with.length(0);
    });
    it('should mount with custom title', async () => {
        const wrapper = await mountShallow(Modal, {
            props: {
                title: 'Title',
            }
        });
        const component = wrapper.vm;

        expect(component.title).to.equal('Title');
        expect(wrapper.find('.modal-mask').text()).to.equal('Title');
    });
    it('should mount with close-on-background-click enabled', async () => {
        const wrapper = await mountShallow(Modal, {
            props: {
                closeOnBackgroundClick: true,
            }
        });
        const component = wrapper.vm;

        component.closeModal = sinon.spy();

        expect(component.closeOnBackgroundClick, 'component prop closeOnBackgroundClick').to.equal(true);
        wrapper.find('.modal-mask').trigger('click');
        expect(component.closeModal.calledOnce, 'close modal called').to.equal(true);
    });
    it('should mount with close icon enabled', async () => {
        const wrapper = await mountShallow(Modal, {
            props: {
                hasCloseIcon: true,
            }
        });
        const component = wrapper.vm;

        expect(component.hasCloseIcon).to.equal(true);
        expect(wrapper.find('.icon-close-modal').exists()).to.equal(true);
    });
    it('should mount with error-modal setting enabled', async () => {
        const wrapper = await mountShallow(Modal, {
            props: {
                isErrorModal: true,
            }
        });
        const component = wrapper.vm;

        expect(component.isErrorModal).to.equal(true);
        expect(wrapper.find('.modal-container').classes()).to.contain('modal-error');
    });
    it('should mount with show-actions disabled', async () => {
        const wrapper = await mountShallow(Modal, {
            props: {
                showActions: false,
            }
        });
        const component = wrapper.vm;

        expect(component.showActions).to.equal(false);
        expect(wrapper.find('.modal-actions').exists()).to.equal(false);
    });
});
