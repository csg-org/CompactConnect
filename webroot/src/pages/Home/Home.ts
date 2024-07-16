//
//  Home.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 4/30/2021.
//

import { Component, Vue } from 'vue-facing-decorator';
import Section from '@components/Section/Section.vue';
import StateUpload from '@components/StateUpload/StateUpload.vue';

@Component({
    name: 'HomePage',
    components: {
        Section,
        StateUpload,
    }
})
export default class Home extends Vue {
}
