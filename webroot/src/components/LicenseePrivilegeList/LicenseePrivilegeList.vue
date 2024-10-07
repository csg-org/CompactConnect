<!--
    LicenseePrivilegeList.vue
    CompactConnect

    Created by InspiringApps on 10/3/2024.
-->

<template>
    <div class="licensee-privilege-list-container">
        <div class="licensee-privilege-list-header-row">
            <img class="priv-list-img" src="@assets/images/ellipse.svg" alt="Privilege List Logo" />
            <span class="priv-list-title">Current privileges</span>
        </div>
        <div class="priv-list-table">
            <div class="state-name-list">
                <div class="state-title state-name">State</div>
                <div
                    v-for="(state, i) in privStateList"
                    :key="state.abbrev+i"
                    class="state-name"
                >
                    {{state}}
                </div>
            </div>
            <div class="expiry-list">
                <div class="expiry-title expiry">Expires</div>
                <div
                    v-for="(expiry, i) in privExpirationList"
                    :key="expiry+i"
                    class="expiry"
                >
                    {{expiry}}
                </div>
            </div>
        </div>
    </div>
</template>

<script lang="ts" src="./LicenseePrivilegeList.ts"></script>
<style scoped lang="less" src="./LicenseePrivilegeList.less"></style>
