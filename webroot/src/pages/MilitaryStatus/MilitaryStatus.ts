//
//  MilitaryStatus.ts
//  CompactConnect
//
//  Created by InspiringApps on 12/20/2024.
//

import { Component, Vue } from 'vue-facing-decorator';
import InputButton from '@components/Forms/InputButton/InputButton.vue';
import { Compact } from '@models/Compact/Compact.model';

@Component({
    name: 'MilitaryStatus',
    components: {
        InputButton
    }
})
export default class MilitaryStatus extends Vue {
    //
    // Data
    //

    //
    // Lifecycle
    //

    //
    // Computed
    //
    get statusTitleText(): string {
        return this.$t('licensing.status').toUpperCase();
    }

    get status(): string {
        return 'Active';
    }

    get affiliationTypeTitle(): string {
        return this.$t('military.affiliationType').toUpperCase();
    }

    get affiliationType(): string {
        return 'Active-duty military member';
    }

    get previouslyUploadedTitle(): string {
        return this.$t('military.previouslyUploadedDocuments').toUpperCase();
    }

    get currentCompact(): Compact | null {
        return this.userStore?.currentCompact || null;
    }

    get currentCompactType(): string | null {
        return this.currentCompact?.type || null;
    }

    get userStore(): any {
        return this.$store.state.user;
    }

    //
    // Methods
    //
    goBack() {
        console.log('go back');
    }

    endAffiliation() {
        console.log('ending');
    }

    editInfo() {
        if (this.currentCompactType) {
            this.$router.push({
                name: 'UpdateMilitaryStatus',
                params: { compact: this.currentCompactType }
            });
        }
    }
}
