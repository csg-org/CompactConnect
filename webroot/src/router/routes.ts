//
//  routes.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 4/12/20.
//

import { RouteRecordRaw as RouteConfig } from 'vue-router';
import guards from '@router/_guards';

// The route array
const routes: Array<RouteConfig> = [
    {
        path: '/',
        redirect: '/Login',
        beforeEnter: guards.noAuthGuard,
    },
    {
        path: '/Register',
        name: 'RegisterLicensee',
        component: () => import(/* webpackChunkName: "register" */ '@pages/RegisterLicensee/RegisterLicensee.vue'),
        beforeEnter: guards.noAuthGuard,
    },
    {
        path: '/Login',
        name: 'Login',
        component: () => import(/* webpackChunkName: "home" */ '@pages/Login/Login.vue'),
        beforeEnter: guards.noAuthGuard,
    },
    {
        path: '/auth/callback',
        name: 'AuthCallback',
        component: () => import(/* webpackChunkName: "home" */ '@pages/AuthCallback/AuthCallback.vue'),
        meta: { skipTransition: true },
    },
    {
        path: '/Logout',
        name: 'Logout',
        component: () => import(/* webpackChunkName: "home" */ '@pages/Logout/Logout.vue'),
    },
    {
        path: '/Home',
        name: 'Home',
        component: () => import(/* webpackChunkName: "home" */ '@pages/Home/Home.vue'),
        meta: { requiresAuth: true, licenseeAccess: true, staffAccess: true },
    },
    {
        path: '/Account',
        name: 'Account',
        component: () => import(/* webpackChunkName: "home" */ '@pages/Account/Account.vue'),
        meta: { requiresAuth: true, licenseeAccess: true, staffAccess: true },
    },
    {
        path: '/:compact/Licensing',
        name: 'Licensing',
        component: () => import(/* webpackChunkName: "licensing" */ '@pages/LicensingList/LicensingList.vue'),
        meta: { requiresAuth: true, staffAccess: true },
    },
    {
        path: '/:compact/Licensing/:licenseeId',
        name: 'LicensingDetail',
        component: () => import(/* webpackChunkName: "licensing" */ '@pages/LicensingDetail/LicensingDetail.vue'),
        meta: { requiresAuth: true, staffAccess: true },
    },
    {
        path: '/:compact/Settings',
        name: 'CompactSettings',
        component: () => import(/* webpackChunkName: "licensing" */ '@pages/CompactSettings/CompactSettings.vue'),
        meta: { requiresAuth: true, staffAccess: true },
    },
    {
        path: '/:compact/StateUpload',
        name: 'StateUpload',
        component: () => import(/* webpackChunkName: "upload" */ '@pages/StateUpload/StateUpload.vue'),
        meta: { requiresAuth: true, staffAccess: true },
    },
    {
        path: '/:compact/Users',
        name: 'Users',
        component: () => import(/* webpackChunkName: "users" */ '@pages/UserList/UserList.vue'),
        meta: { requiresAuth: true, staffAccess: true },
    },
    {
        path: '/:compact/LicenseeDashboard',
        name: 'LicenseeDashboard',
        component: () => import(/* webpackChunkName: "licenseeDashboard" */ '@pages/LicenseeDashboard/LicenseeDashboard.vue'),
        meta: { requiresAuth: true, licenseeAccess: true, },
    },
    {
        path: '/:compact/MilitaryStatus',
        name: 'MilitaryStatus',
        component: () => import(/* webpackChunkName: "militaryStatus" */ '@pages/MilitaryStatus/MilitaryStatus.vue'),
        meta: { requiresAuth: true, licenseeAccess: true, },
    },
    {
        path: '/:compact/MilitaryStatus/Update',
        name: 'MilitaryStatusUpdate',
        component: () => import(/* webpackChunkName: "militaryStatusUpdate" */ '@pages/MilitaryStatusUpdate/MilitaryStatusUpdate.vue'),
        meta: { requiresAuth: true, licenseeAccess: true, },
    },
    {
        path: '/:compact/Privileges/SelectPrivileges',
        name: 'SelectPrivileges',
        component: () => import(/* webpackChunkName: "privilegePurchase" */ '@pages/SelectPrivileges/SelectPrivileges.vue'),
        meta: { requiresAuth: true, licenseeAccess: true, },
    },
    {
        path: '/:compact/Privileges/FinalizePurchase',
        name: 'FinalizePrivilegePurchase',
        component: () => import(/* webpackChunkName: "privilegePurchase" */ '@pages/FinalizePrivilegePurchase/FinalizePrivilegePurchase.vue'),
        meta: { requiresAuth: true, licenseeAccess: true, },
    },
    {
        path: '/:compact/Privileges/PurchaseSuccessful',
        name: 'PurchaseSuccessful',
        component: () => import(/* webpackChunkName: "privilegePurchase" */ '@pages/PurchaseSuccessful/PurchaseSuccessful.vue'),
        meta: { requiresAuth: true, licenseeAccess: true, },
    },
    {
        path: '/:compact/Privileges/Attestation',
        name: 'PrivilegePurchaseAttestation',
        component: () => import(/* webpackChunkName: "privilegePurchase" */ '@pages/PrivilegePurchaseAttestation/PrivilegePurchaseAttestation.vue'),
        meta: { requiresAuth: true, licenseeAccess: true, },
    },
    {
        path: '/styleguide',
        name: 'StyleGuide',
        component: () => import(/* webpackChunkName: "styleGuide" */ '@pages/StyleGuide/StyleGuide.vue'),
    },
    //
    // KEEP "*" path AT THE BOTTOM OF THIS ARRAY
    //
    {
        path: '/:pathMatch(.*)*',
        name: '404',
        component: () => import(/* webpackChunkName: "home" */ '@pages/404/404.vue'),
    },
];

export default routes;
