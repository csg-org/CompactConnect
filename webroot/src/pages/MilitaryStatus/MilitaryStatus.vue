<!--
    MilitaryStatus.vue
    CompactConnect

    Created by InspiringApps on 12/20/2024.
-->

<template>
   <div class="military-status-container">
    <div class="military-status-content-container">
        <InputButton
            :label="$t('common.back')"
            :aria-label="$t('common.back')"
            :isTextLike="true"
            :shouldHideMargin="true"
            class="back-btn"
            @click="goBack"
        />
        <div class="military-status-title">
            {{ $t('military.militaryStatusTitle') }}
        </div>
        <MilitaryAffiliationInfoBlock
            :licensee="licensee"
            :currentCompactType="currentCompactType"
            :shouldShowEditButtons="true"
        />
    </div>
   </div>
</template>

<script lang="ts" src="./MilitaryStatus.ts"></script>
<style scoped lang="less" src="./MilitaryStatus.less"></style>
