//
//  InputFile.spec.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 7/8/2020.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import InputFile from '@components/Forms/InputFile/InputFile.vue';
import { FormInput } from '@models/FormInput/FormInput.model';

describe('InputFile component', async () => {
    it('should mount the component', async () => {
        const wrapper = await mountShallow(InputFile, {
            props: {
                formInput: new FormInput(),
            },
        });

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(InputFile).exists()).to.equal(true);
    });
});
