//
//  MilitaryDocumentRow.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 4/30/2021.
//

import { Component, Prop, Vue } from 'vue-facing-decorator';
import DownloadIcon from '@components/Icons/DownloadFile/DownloadFile.vue';

@Component({
    name: 'MilitaryDocumentRow',
    components: {
        DownloadIcon,
    },
})
export default class MilitaryDocumentRow extends Vue {
    @Prop({ required: true }) item!: any;
    @Prop({ default: false }) isHeaderRow?: boolean;
    @Prop({ default: false }) isDownloadAvailable?: boolean;
}
