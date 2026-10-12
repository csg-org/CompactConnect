//
//  LicenseeRow.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 7/3/2024.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import LicenseeRow from '@components/Licensee/LicenseeRow/LicenseeRow.vue';
import { Licensee } from '@models/Licensee/Licensee.model';
import { AppModes } from '@/app.config';
import store from '@store/index';

describe('LicenseeRow component', async () => {
    it('should mount the component', async () => {
        const wrapper = await mountShallow(LicenseeRow, {
            props: {
                listId: 'test',
                item: new Licensee(),
            },
        });

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(LicenseeRow).exists()).to.equal(true);
    });

    describe('phone-number visibility', () => {
        beforeEach(async () => {
            await store.dispatch('setAppMode', AppModes.SOCIAL_WORK);
        });

        it('should display the phone number for a non-public search', async () => {
            const wrapper = await mountShallow(LicenseeRow, {
                props: {
                    listId: 'test',
                    isPublicSearch: false,
                    item: Object.assign(new Licensee(), {
                        isPublicSearch: false,
                    }),
                },
            });

            expect(wrapper.find('.phone-number').exists()).to.equal(true);
        });
        it('should hide the phone number when the row is used for a public search', async () => {
            const wrapper = await mountShallow(LicenseeRow, {
                props: {
                    listId: 'test',
                    isPublicSearch: true,
                    item: Object.assign(new Licensee(), {
                        isPublicSearch: false,
                    }),
                },
            });

            expect(wrapper.find('.phone-number').exists()).to.equal(false);
        });
        it('should hide the phone number when the item is from a public search', async () => {
            const wrapper = await mountShallow(LicenseeRow, {
                props: {
                    listId: 'test',
                    isPublicSearch: false,
                    item: Object.assign(new Licensee(), {
                        isPublicSearch: true,
                    }),
                },
            });

            expect(wrapper.find('.phone-number').exists()).to.equal(false);
        });
    });
});
