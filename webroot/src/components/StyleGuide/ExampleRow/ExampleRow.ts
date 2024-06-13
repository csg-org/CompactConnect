//
//  ExampleRow.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 4/30/2021.
//  Copyright © 2024. InspiringApps. All rights reserved.
//

import { Component, Prop, Vue } from 'vue-facing-decorator';

@Component
export default class ExampleRow extends Vue {
    @Prop({ required: true }) item!: any;
    @Prop({ default: false }) isHeaderRow?: boolean;
}
