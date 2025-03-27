<!--
    PrivilegeDetailBlock.vue
    CompactConnect

    Created by InspiringApps on 3/19/2025.
-->

<template>
    <div class="core-info-block">
        <div class="summary">
            <h3>{{$t('licensing.privilegeSummary')}}</h3>
            <div class="privilege-summary-details">
                <div class="info-item-container">
                    <div class="info-item-title">{{issuedTitle}}</div>
                    <div class="info-item">{{issuedContent}}</div>
                </div>
                <div class="info-item-container">
                    <div class="info-item-title">{{$t('licensing.status')}}</div>
                    <div class="info-item">{{statusDisplay}}</div>
                </div>
                <div class="info-item-container">
                    <div class="info-item-title">{{$t('licensing.privilegeNumSymbol')}}</div>
                    <div class="info-item" >{{privilegeId}}</div>
                </div>
                <div class="info-item-container">
                    <div class="info-item-title">{{disciplineTitle}}</div>
                    <div class="info-item">{{disciplineContent}}</div>
                </div>
            </div>
        </div>
        <div class="history">
            <h3>{{$t('common.history')}}</h3>
            <PrivilegeHistory :privilege="privilege" />
        </div>
    </div>
</template>

<script lang="ts" src="./PrivilegeDetailBlock.ts"></script>
<style scoped lang="less" src="./PrivilegeDetailBlock.less"></style>
