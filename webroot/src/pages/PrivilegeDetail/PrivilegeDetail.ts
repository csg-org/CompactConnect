//
//  PrivilegeDetail.ts
//  CompactConnect
//
//  Created by InspiringApps on 3/18/2025.
//

import { Component, Vue } from 'vue-facing-decorator';
import InputButton from '@components/Forms/InputButton/InputButton.vue';
import PrivilegeDetailBlock from '@components/PrivilegeDetailBlock/PrivilegeDetailBlock.vue';
import { License } from '@models/License/License.model';

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
        return (this.$route.params.privilegeId as string || '');
    }

    get privilege(): License {
        return this.$store.getters['user/getPrivilegeById'](this.privilegeId) || new License();
    }

    get privilegeTitle(): string {
        return `${this.privilege?.licenseTypeAbbreviation()} - ${this.privilege?.issueState?.name()}`;
    }

    //
    // Methods
    //
    goBack() {
        this.$router.back();
    }
}
