<!--
    PracticeStates.vue
    CompactConnect

    Created by InspiringApps on 9/24/2026.
-->

<template>
    <div class="practice-list-container">
        <div v-if="!licenseeAllCredentials.length" class="no-practice">
            {{ $t('licensing.providerNoPracticeStates') }}
        </div>
        <div v-else class="practice-list" role="table">
            <div v-if="$matches.tablet.min" class="practice-row header" role="row">
                <div class="practice-cell state" role="columnheader">
                    {{ $t('common.state') }}
                </div>
                <div class="practice-cell status" role="columnheader">
                    {{ $t('common.status') }}
                </div>
                <div class="practice-cell discipline" role="columnheader">
                    {{ $t('licensing.discipline') }}
                </div>
                <div v-if="!isPublicSearch" class="practice-cell actions" role="columnheader"></div>
            </div>
            <div
                v-for="(credential, index) in licenseeAllCredentials"
                :key="index"
                class="practice-row"
                role="row"
            >
                <div class="practice-cell state" role="cell">
                    <span v-if="$matches.phone.only" class="cell-title">
                        {{ $t('common.state') }}:
                    </span>
                    <span class="cell-value">{{ credential.issueState.name() }}</span>
                </div>
                <div class="practice-cell status" role="cell">
                    <span v-if="$matches.phone.only" class="cell-title">
                        {{ $t('common.status') }}:
                    </span>
                    <span class="cell-value">{{ getStatusDisplay(credential) }}</span>
                </div>
                <div class="practice-cell discipline" role="cell">
                    <span v-if="$matches.phone.only" class="cell-title">
                        {{ $t('licensing.discipline') }}:
                    </span>
                    <span class="cell-value">{{ getDisciplineContent(credential) }}</span>
                </div>
                <div v-if="!isPublicSearch" class="practice-cell actions" role="cell">
                    <span v-if="$matches.phone.only" class="cell-title">
                        {{ $t('common.actions') }}:
                    </span>
                    <LicenseActionsModal
                        :license="credential"
                        :licensee="licensee"
                        :type="(credential.isPrivilege) ? 'privilege' : 'license'"
                    />
                </div>
            </div>
        </div>
    </div>
</template>

<script lang="ts" src="./PracticeStates.ts"></script>
<style scoped lang="less" src="./PracticeStates.less"></style>
