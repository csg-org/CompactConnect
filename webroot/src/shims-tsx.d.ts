//
//  shims-tsx.d.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 4/12/20.
//

import Vue, { VNode } from 'vue';

declare global {
    namespace JSX {
        // tslint:disable no-empty-interface
        interface Element extends VNode {}
        // tslint:disable no-empty-interface
        interface ElementClass extends Vue {}
        interface IntrinsicElements {
            [elem: string]: any;
        }
    }
    interface Array<T> {
        at(index: number): T | undefined;
    }
}
