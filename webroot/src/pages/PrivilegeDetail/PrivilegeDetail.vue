<!--
    PrivilegeDetail.vue
    CompactConnect

    Created by InspiringApps on 3/18/2025.
-->

<template>
    <div class="privilege-detail-container">
        <div class="privilege-detail-content-container">
            <InputButton
                :label="$t('common.back')"
                :aria-label="$t('common.back')"
                :isTextLike="true"
                :shouldHideMargin="true"
                class="back-btn"
                @click="goBack"
            />
            <div class="privilege-detail-title">
                {{ $t('military.militaryStatusTitle') }}
            </div>
            <PrivilegeDetailBlock
                :licensee="licensee"
                :currentCompactType="currentCompactType"
                :shouldShowEditButtons="true"
            />
        </div>
    </div>
</template>

<script lang="ts" src="./PrivilegeDetail.ts"></script>
<style scoped lang="less" src="./PrivilegeDetail.less"></style>
