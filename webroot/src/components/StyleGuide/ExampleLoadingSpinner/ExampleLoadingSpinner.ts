//
//  ExampleLoadingSpinner.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 5/5/2021.
//

import { Component, Vue, toNative } from 'vue-facing-decorator';
import Section from '@components/Section/Section.vue';
import InputButton from '@components/Forms/InputButton/InputButton.vue';

@Component({
    name: 'ExampleLoadingSpinner',
    components: {
        Section,
        InputButton,
    }
})
class ExampleLoadingSpinner extends Vue {
    //
    // Data
    //
    globalStore: any = {};

    //
    // Lifecycle
    //
    created() {
        this.globalStore = this.$store.state;
    }

    //
    // Methods
    //
    showSpinner() {
        this.$store.dispatch('startLoading');

        setTimeout(this.hideSpinner, 2000);
    }

    hideSpinner() {
        this.$store.dispatch('endLoading');
    }
}

export default toNative(ExampleLoadingSpinner);

// export { ExampleLoadingSpinner };
