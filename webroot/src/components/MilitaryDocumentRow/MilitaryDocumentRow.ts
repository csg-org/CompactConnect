//
//  MilitaryDocumentRow.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 4/30/2021.
//

import { Component, Prop, Vue } from 'vue-facing-decorator';

@Component
export default class MilitaryDocumentRow extends Vue {
    @Prop({ required: true }) item!: any;
    @Prop({ default: false }) isHeaderRow?: boolean;
}
