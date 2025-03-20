//
//  PrivilegeDetail.ts
//  CompactConnect
//
//  Created by InspiringApps on 3/18/2025.
//

import { Component, Vue } from 'vue-facing-decorator';
import InputButton from '@components/Forms/InputButton/InputButton.vue';
import PrivilegeDetailBlock from '@components/PrivilegeDetailBlock/PrivilegeDetailBlock.vue';

@Component({
    name: 'PrivilegeDetail',
    components: {
        InputButton,
        PrivilegeDetailBlock
    }
})
export default class PrivilegeDetail extends Vue {
    //
    // Data
    //

    //
    // Lifecycle
    //

    //
    // Computed
    //
    get privilegeId(): string {
        return this.$route.prive
    }

    //
    // Methods
    //
}
