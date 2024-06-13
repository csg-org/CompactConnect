//
//  InputTextarea.spec.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 7/21/2020.
//  Copyright © 2024. InspiringApps. All rights reserved.
//

import { expect } from 'chai';
import { mountShallow, mountFull } from '@tests/helpers/setup';
import InputTextarea from '@components/Forms/InputTextarea/InputTextarea.vue';
import { FormInput } from '@models/FormInput/FormInput.model';

describe('InputTextarea component', async () => {
    it('should mount the component', async () => {
        const wrapper = await mountShallow(InputTextarea, {
            props: {
                formInput: new FormInput(),
            }
        });

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(InputTextarea).exists()).to.equal(true);
    });
    it('should have default styles', async () => {
        const wrapper = await mountFull(InputTextarea, {
            props: {
                formInput: new FormInput(),
            }
        });
        const textarea = wrapper.find('textarea');

        expect(textarea.classes(), 'do not resize by default').not.to.contain('resize-x');
        expect(textarea.classes(), 'do not resize by default').not.to.contain('resize-y');
        expect(textarea.classes(), 'do not resize by default').not.to.contain('resize-all');
        expect(textarea.classes(), 'do not match border color with bg by default').not.to.contain('border-color-match-bg');
    });
    it('should have reset-x styles', async () => {
        const wrapper = await mountFull(InputTextarea, {
            props: {
                formInput: new FormInput(),
                shouldResizeX: true,
            }
        });
        const textarea = wrapper.find('textarea');

        expect(textarea.classes(), 'do not resize by default').to.contain('resize-x');
        expect(textarea.classes(), 'do not resize by default').not.to.contain('resize-y');
        expect(textarea.classes(), 'do not resize by default').not.to.contain('resize-all');
        expect(textarea.classes(), 'do not match border color with bg by default').not.to.contain('border-color-match-bg');
    });
    it('should have reset-y styles', async () => {
        const wrapper = await mountFull(InputTextarea, {
            props: {
                formInput: new FormInput(),
                shouldResizeY: true,
            }
        });
        const textarea = wrapper.find('textarea');

        expect(textarea.classes(), 'do not resize by default').not.to.contain('resize-x');
        expect(textarea.classes(), 'do not resize by default').to.contain('resize-y');
        expect(textarea.classes(), 'do not resize by default').not.to.contain('resize-all');
        expect(textarea.classes(), 'do not match border color with bg by default').not.to.contain('border-color-match-bg');
    });
    it('should have reset-all styles', async () => {
        const wrapper = await mountFull(InputTextarea, {
            props: {
                formInput: new FormInput(),
                shouldResize: true,
            }
        });
        const textarea = wrapper.find('textarea');

        expect(textarea.classes(), 'do not resize by default').not.to.contain('resize-x');
        expect(textarea.classes(), 'do not resize by default').not.to.contain('resize-y');
        expect(textarea.classes(), 'do not resize by default').to.contain('resize-all');
        expect(textarea.classes(), 'do not match border color with bg by default').not.to.contain('border-color-match-bg');
    });
    it('should have border-color styles', async () => {
        const wrapper = await mountFull(InputTextarea, {
            props: {
                formInput: new FormInput(),
                shouldBorderMatchBgColor: true,
            }
        });
        const textarea = wrapper.find('textarea');

        expect(textarea.classes(), 'do not resize by default').not.to.contain('resize-x');
        expect(textarea.classes(), 'do not resize by default').not.to.contain('resize-y');
        expect(textarea.classes(), 'do not resize by default').not.to.contain('resize-all');
        expect(textarea.classes(), 'do not match border color with bg by default').to.contain('border-color-match-bg');
    });
});
