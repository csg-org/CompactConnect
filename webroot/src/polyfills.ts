//
//  polyfills.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 4/12/20.
//  Copyright © 2024. InspiringApps. All rights reserved.
//

import fromEntries from 'object.fromentries';
import { TextEncoder } from 'text-encoding-shim';

// Object.fromEntries
if (!Object.fromEntries) {
    fromEntries.shim();
    // console.log('polyfill applied: Object.fromEntries'); // @DEBUG
}

// window.TextEncoder
if (typeof window.TextEncoder === 'undefined') {
    (window as any).TextEncoder = TextEncoder;
    // console.log('polyfill applied: TextEncoder'); // @DEBUG
}
