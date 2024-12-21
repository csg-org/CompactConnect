<!--
    MilitaryStatus.vue
    CompactConnect

    Created by InspiringApps on 12/20/2024.
-->

<template>
   <div class="military-status-container">
        <InputButton
            :label="$t('common.back')"
            :aria-label="$t('common.back')"
            :isTextLike="true"
            class="back-btn"
            @click="goBack"
        />
        <div class="military-status-title">
            {{ $t('military.militaryStatusTitle') }}
        </div>
        <div class="core-info-block">
            <div class="status-chunk">
                <div class="chunk-title"></div>
            </div>
            <div class="type-chunk">
                <div class="chunk-title"></div>
            </div>
            <div class="table-chunk">
                <div class="chunk-title"></div>
            </div>
        </div>
   </div>
</template>

<script lang="ts" src="./MilitaryStatus.ts"></script>
<style scoped lang="less" src="./MilitaryStatus.less"></style>
