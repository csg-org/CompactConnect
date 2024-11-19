//
//  Account.ts
//  CompactConnect
//
//  Created by InspiringApps on 11/4/2024.
//

import { Component, Vue } from 'vue-facing-decorator';
import Section from '@components/Section/Section.vue';
import UserAccount from '@components/UserAccount/UserAccount.vue';

@Component({
    name: 'Account',
    components: {
        Section,
        UserAccount,
    }
})
export default class Account extends Vue {
}
